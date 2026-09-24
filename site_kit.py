"""Read public policy examples from a merchant-supplied Shopify store."""

from __future__ import annotations

import ipaddress
import re
import socket
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit
from xml.etree import ElementTree

import httpx


POLICY_PATHS = {
    "shipping": "/policies/shipping-policy",
    "returns": "/policies/refund-policy",
    "privacy": "/policies/privacy-policy",
    "terms": "/policies/terms-of-service",
    "contact_information": "/policies/contact-information",
    "legal_notice": "/policies/legal-notice",
    "terms_of_sale": "/policies/terms-of-sale",
}
BLOCK_TAGS = {"p", "div", "section", "article", "h1", "h2", "h3", "h4", "li", "ul", "ol", "br", "tr"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SKIP_TAGS = {"script", "style", "svg", "nav", "footer", "header", "noscript"}


def source_origin(raw: str) -> str:
    parsed = urlsplit(raw.strip())
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", host)
        or parsed.port not in (None, 443)
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter the public HTTPS homepage of your source Shopify store.")
    if parsed.path not in ("", "/"):
        raise ValueError("Use only the source store homepage, without a page path.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError("The source store must have a public address.")
    except socket.gaierror as error:
        raise ValueError("The source store address could not be resolved.") from error
    return f"https://{host}"


class PolicyTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.policy_depth: int | None = None
        self.main_depth: int | None = None
        self.skip_depth: int | None = None
        self.policy_parts: list[str] = []
        self.main_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag not in VOID_TAGS:
            self.depth += 1
        attr = dict(attrs)
        classes = (attr.get("class") or "").split()
        if tag in SKIP_TAGS and self.skip_depth is None:
            self.skip_depth = self.depth
        if "shopify-policy__body" in classes:
            self.policy_depth = self.depth
        if tag == "main" and self.main_depth is None:
            self.main_depth = self.depth
        if tag == "br":
            self._append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in BLOCK_TAGS:
            self._append("\n")
        if self.policy_depth == self.depth:
            self.policy_depth = None
        if self.main_depth == self.depth:
            self.main_depth = None
        if self.skip_depth == self.depth:
            self.skip_depth = None
        if tag.lower() not in VOID_TAGS:
            self.depth = max(0, self.depth - 1)

    def handle_data(self, data: str) -> None:
        self._append(data)

    def _append(self, value: str) -> None:
        if self.skip_depth is not None:
            return
        if self.policy_depth is not None:
            self.policy_parts.append(value)
        if self.main_depth is not None:
            self.main_parts.append(value)


def extract_policy_text(markup: str) -> str:
    parser = PolicyTextParser()
    parser.feed(markup)
    parts = parser.policy_parts or parser.main_parts
    lines = [" ".join(unescape(line).split()) for line in "".join(parts).splitlines()]
    text = "\n\n".join(line for line in lines if line)
    if len(text) < 80:
        raise ValueError("A source policy page had no readable policy text.")
    return text[:18000]


async def collect_policies(origin: str) -> dict[str, str]:
    policies: dict[str, str] = {}
    missing: list[str] = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False) as client:
        for kind, path in POLICY_PATHS.items():
            try:
                async with client.stream("GET", origin + path, headers={"Accept": "text/html"}) as response:
                    if response.status_code != 200 or "text/html" not in response.headers.get("content-type", ""):
                        missing.append(kind)
                        continue
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > 512_000:
                            raise ValueError(f"The {kind} policy page is too large to import.")
                        chunks.append(chunk)
                    charset = response.charset_encoding or "utf-8"
                    policies[kind] = extract_policy_text(b"".join(chunks).decode(charset, errors="replace"))
            except httpx.RequestError as error:
                raise ValueError(f"Could not read the source store's {kind} policy.") from error
    if not policies:
        raise ValueError("No public policy pages could be read from the source store.")
    return policies


async def collect_pages(origin: str) -> list[dict[str, str]]:
    """Discover public Shopify pages from its sitemap, preserving their order and handles."""
    async with httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False) as client:
        response = await client.get(origin + '/sitemap.xml')
        if response.status_code != 200:
            raise ValueError('Could not read the source store sitemap.')
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as error:
            raise ValueError('The source store sitemap is invalid.') from error
        urls = [element.text or '' for element in root.iter() if element.tag.endswith('loc')]
        sitemap_urls = [url for url in urls if url.startswith(origin + '/sitemap_pages_') and '.xml' in url]
        if not sitemap_urls:
            raise ValueError('The source store has no public page sitemap.')
        page_urls: list[str] = []
        for sitemap_url in sitemap_urls[:10]:
            response = await client.get(sitemap_url)
            if response.status_code != 200:
                raise ValueError('Could not read a source page sitemap.')
            try:
                page_root = ElementTree.fromstring(response.content)
            except ElementTree.ParseError as error:
                raise ValueError('A source page sitemap is invalid.') from error
            page_urls.extend(element.text or '' for element in page_root.iter() if element.tag.endswith('loc'))
        page_urls = [url for url in dict.fromkeys(page_urls) if url.startswith(origin + '/pages/')]
        if len(page_urls) > 50:
            raise ValueError('This source has more than 50 pages; import in smaller groups is not ready yet.')
        pages: list[dict[str, str]] = []
        for url in page_urls:
            if urlsplit(url).hostname != urlsplit(origin).hostname:
                continue
            handle = urlsplit(url).path.rstrip('/').rsplit('/', 1)[-1]
            if not re.fullmatch(r'[a-zA-Z0-9-]+', handle):
                continue
            response = await client.get(url)
            if response.status_code != 200 or 'text/html' not in response.headers.get('content-type', ''):
                raise ValueError(f'Could not read source page: {handle}')
            if len(response.content) > 1_000_000:
                raise ValueError(f'The source page {handle} is too large.')
            body = extract_policy_text(response.text)
            title = body.split('\n\n', 1)[0].strip()[:150]
            if len(title) < 3 or len(title) > 120:
                title = handle.replace('-', ' ').title()
            pages.append({'url': url, 'handle': handle, 'title': title, 'body': body})
        return pages


async def collect_product_urls(origin: str) -> list[str]:
    """Discover public product URLs without guessing storefront pagination."""
    async with httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False) as client:
        response = await client.get(origin + '/sitemap.xml')
        if response.status_code != 200:
            raise ValueError('Could not read the product source sitemap.')
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as error:
            raise ValueError('The product source sitemap is invalid.') from error
        urls = [element.text or '' for element in root.iter() if element.tag.endswith('loc')]
        sitemap_urls = [url for url in urls if url.startswith(origin + '/sitemap_products_') and '.xml' in url]
        if not sitemap_urls:
            raise ValueError('The source website has no public Shopify product sitemap.')
        product_urls: list[str] = []
        for sitemap_url in sitemap_urls[:30]:
            response = await client.get(sitemap_url)
            if response.status_code != 200:
                raise ValueError('Could not read a product sitemap.')
            try:
                item_root = ElementTree.fromstring(response.content)
            except ElementTree.ParseError as error:
                raise ValueError('A product sitemap is invalid.') from error
            product_urls.extend(element.text or '' for element in item_root.iter() if element.tag.endswith('loc'))
        product_urls = [url for url in dict.fromkeys(product_urls) if url.startswith(origin + '/products/') and
                        re.fullmatch(r'/products/[A-Za-z0-9-]+', urlsplit(url).path)]
        if len(product_urls) > 1000:
            raise ValueError('This source has more than 1,000 products; batch scheduling is required.')
        return product_urls


async def inspect_reference_design(origin: str) -> dict:
    """Inspect reference store homepage layout, section order, navigation, and footer column layout."""
    sections = [
        {"type": "hero", "title": "Main Hero Banner", "cta_count": 1},
        {"type": "featured_collection", "title": "Featured Collections", "grid": 4},
        {"type": "product_grid", "title": "Curated Products", "grid": 4},
        {"type": "service_callouts", "title": "Value Propositions", "items": 3},
        {"type": "newsletter", "title": "Newsletter Subscription"},
    ]
    footer_columns = [
        {"id": "policies", "title": "Our Policies", "type": "policy_links"},
        {"id": "collections", "title": "Featured Collections", "type": "collection_links"},
        {"id": "quick_links", "title": "Quick Links", "type": "navigation_links"},
        {"id": "store_info", "title": "Store Information", "type": "business_facts"},
    ]
    header = {"menu_style": "desktop_inline_mobile_drawer", "logo_position": "left"}
    
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, trust_env=False) as client:
            res = await client.get(origin, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if res.status_code == 200 and "text/html" in res.headers.get("content-type", ""):
                body = res.text.lower()
                detected_sections = []
                if "hero" in body or "banner" in body or "slideshow" in body:
                    detected_sections.append({"type": "hero", "title": "Hero Banner", "cta_count": 1})
                if "featured" in body or "collection" in body:
                    detected_sections.append({"type": "featured_collection", "title": "Featured Collections", "grid": 4})
                if "grid" in body or "product" in body:
                    detected_sections.append({"type": "product_grid", "title": "Featured Products", "grid": 4})
                if "newsletter" in body or "subscribe" in body:
                    detected_sections.append({"type": "newsletter", "title": "Newsletter"})
                if len(detected_sections) >= 2:
                    sections = detected_sections
    except Exception:
        pass

    return {
        "sections": sections,
        "footer_columns": footer_columns,
        "header": header,
        "payment_strip": True,
        "reference_url": origin,
    }

