"""Generate a consistent realistic product gallery with Gemini and attach it to Shopify."""

from __future__ import annotations

import base64
import ipaddress
import re
import socket
from io import BytesIO
from urllib.parse import urlsplit

import httpx
from PIL import Image, ImageDraw, ImageFilter, UnidentifiedImageError

GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-3.1-flash-image:generateContent"
SHOPIFY_API_VERSION = "2024-01"
IMAGE_ROLES = ("hero", "detail", "lifestyle")


class ImagePipelineError(Exception):
    pass


def _public_image_url(url: str) -> None:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or not re.fullmatch(r"[a-z0-9.-]+", host)
            or parsed.port not in (None, 443) or parsed.username or parsed.password):
        raise ImagePipelineError("The source product image needs a public HTTPS URL.")
    try:
        addresses = {entry[4][0] for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as error:
        raise ImagePipelineError("The source product image host could not be resolved.") from error
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ImagePipelineError("The source product image must use a public host.")


async def _download_reference(client: httpx.AsyncClient, url: str) -> tuple[str, bytes]:
    if isinstance(url, str) and url.startswith("//"):
        url = "https:" + url
    elif isinstance(url, str) and url.startswith("http://"):
        url = "https://" + url[7:]
    _public_image_url(url)
    try:
        async with client.stream("GET", url, headers={"Accept": "image/png,image/jpeg,image/webp"}) as response:
            if response.status_code != 200:
                raise ImagePipelineError("The source product photo could not be downloaded.")
            mime = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if mime not in {"image/png", "image/jpeg", "image/webp"}:
                raise ImagePipelineError("The source product photo must be PNG, JPEG, or WebP.")
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > 8_000_000:
                    raise ImagePipelineError("The source product photo is too large.")
                chunks.append(chunk)
            content = b"".join(chunks)
            if not content:
                raise ImagePipelineError("The source product photo is empty.")
            return mime, content
    except httpx.RequestError as error:
        raise ImagePipelineError("The source product photo could not be downloaded.") from error


def _role_prompt(role: str, *, product_title: str, source_title: str, store_name: str,
                 primary_color: str, accent_color: str, brand_style: str,
                 target_audience: str, product_facts: str) -> str:
    primary = primary_color.strip() if primary_color else '#2251dc'
    accent = accent_color.strip() if accent_color else '#6f9cff'
    shared = (
        f"Create a photorealistic square ecommerce image for the exact source product {source_title}. "
        f"Destination private-label brand: {store_name}. Brand color palette: primary={primary}, accent={accent}. "
        f"Visual direction: {brand_style or 'clean, credible, premium ecommerce photography'}. "
        f"Audience: {target_audience or 'everyday shoppers in the United States'}. "
        f"1. BRAND COLOR RECOLORING: Re-color and rebrand the product's main painted exterior surfaces, body panels, housing, enclosure, and major frame sections using the destination primary brand color ({primary}) and accent color ({accent}). Replace the original source product's body paint color (such as green, blue, yellow, or orange) with the primary brand color ({primary}) on main body shells, and accent color ({accent}) on trim sections. Keep unpainted functional components (rubber tires, steel/chrome engine parts, black cables, glass, controls) in their natural material finishes. "
        f"2. 3D PERSPECTIVE & NATURAL LOGO PLACEMENT: Apply the exact supplied destination logo to one or more physically plausible product surfaces. When the product has several separate brandable surfaces, use the logo on up to three of them, following the reference placement style. All logos printed on physical product surfaces MUST strictly conform to the 3D perspective, camera angle, surface curvature, material texture, and lighting/reflections of that exact surface. Do NOT draw flat, floating, or skewed 2D text labels. The logo must look 100% factory silk-screened or molded onto the product. "
        f"3. CATALOG VISUAL SYNERGY & REALISM: Render the product with 100% photorealistic commercial quality. Preserve physical product geometry, components, controls, seams, and proportions. Do not invent or remove features or accessories. Maintain a consistent studio style across all catalog products so they look like a unified, high-end private-label brand line. Use a clean, seamless neutral studio background with soft contact floor shadows. Reserve a quiet space in the top-left corner because the exact uploaded logo will also be added there after generation. "
        f"Verified source facts: {product_facts[:1500]}. Final listing title: {product_title}. "
    )
    role_text = {
        "hero": (
            "Make the HERO image: full product visible and centered on a clean neutral studio background, realistic "
            "commercial lighting, accurate soft floor shadow, generous margins, zero callout text."
        ),
        "detail": (
            "Make the DETAIL image: a close three-quarter macro shot highlighting the branded finish, material texture, "
            "construction, or functional control visible in the reference. Zero callout text."
        ),
        "lifestyle": (
            "Make the LIFESTYLE image: a natural, tidy home or outdoor use environment appropriate to the product. "
            "Keep product scale, perspective, and usage physically accurate."
        ),
    }.get(role)
    if not role_text:
        raise ImagePipelineError("Unsupported product image role.")
    return shared + role_text


async def _generate_png(client: httpx.AsyncClient, *, gemini_key: str | list[str], prompt: str,
                        source_mime: str, source_bytes: bytes,
                        logo_mime: str = "", logo_bytes: bytes | None = None,
                        logo_dark_mime: str = "", logo_dark_bytes: bytes | None = None) -> str:
    keys = [gemini_key] if isinstance(gemini_key, str) else list(gemini_key)
    keys = [k.strip() for k in keys if isinstance(k, str) and k.strip()]
    if not keys:
        raise ImagePipelineError("Gemini image generation is not configured.")
    parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": source_mime,
                         "data": base64.b64encode(source_bytes).decode("ascii")}},
    ]
    if logo_bytes and logo_mime in {"image/png", "image/jpeg", "image/webp"}:
        parts.append({"text": "This reference is the light version of the destination logo. Preserve its spelling and proportions."})
        parts.append({"inline_data": {"mime_type": logo_mime,
                                      "data": base64.b64encode(logo_bytes).decode("ascii")}})
    if logo_dark_bytes and logo_dark_mime in {"image/png", "image/jpeg", "image/webp"}:
        parts.append({"text": "This reference is the dark version of the destination logo. Use it when rendering dark branding on light surfaces."})
        parts.append({"inline_data": {"mime_type": logo_dark_mime,
                                      "data": base64.b64encode(logo_dark_bytes).decode("ascii")}})
    last_status = None
    response = None
    for key in keys:
        try:
            res = await client.post(
                GEMINI_URL,
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json={"contents": [{"parts": parts}],
                      "generationConfig": {"responseModalities": ["IMAGE"]}},
            )
            if res.status_code == 200:
                response = res
                break
            last_status = res.status_code
        except httpx.RequestError as error:
            last_status = "network"
            continue
    if response is None or response.status_code != 200:
        raise ImagePipelineError(f"Gemini image generation failed (HTTP {last_status}).")
    try:
        response_parts = response.json()["candidates"][0]["content"]["parts"]
        inline = next(part["inlineData"] for part in response_parts
                      if part.get("inlineData", {}).get("data"))
        encoded = inline["data"]
        raw_bytes = base64.b64decode(encoded, validate=True)
        if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            image_bytes = raw_bytes
        else:
            with Image.open(BytesIO(raw_bytes)) as img:
                out = BytesIO()
                img.convert("RGBA").save(out, format="PNG")
                image_bytes = out.getvalue()
                encoded = base64.b64encode(image_bytes).decode("ascii")
    except (KeyError, IndexError, TypeError, ValueError, StopIteration, UnidentifiedImageError, OSError) as error:
        raise ImagePipelineError("Gemini did not return a usable image.") from error
    if len(image_bytes) > 20_000_000:
        raise ImagePipelineError("The generated image is too large for upload.")
    return encoded


def _add_corner_logo(encoded: str, logo_bytes: bytes | None = None,
                     logo_dark_bytes: bytes | None = None) -> str:
    """Embed the exact uploaded logo cleanly in the top-left corner of a generated PNG.

    Measures average top-left background luminance: uses logo_dark on light backgrounds
    (avg_lum > 140) and light logo (logo) on dark or shaded backgrounds.
    """
    if not logo_bytes and not logo_dark_bytes:
        raise ImagePipelineError("No store logo was provided for corner branding.")
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
        with Image.open(BytesIO(image_bytes)) as source:
            image = source.convert("RGBA")
    except (ValueError, UnidentifiedImageError, OSError) as error:
        raise ImagePipelineError("The generated image or uploaded logo could not be composited.") from error
    if image.width < 128 or image.height < 128:
        raise ImagePipelineError("The generated image has invalid dimensions.")

    margin_x = max(16, round(image.width * 0.035))
    margin_y = max(16, round(image.height * 0.035))

    sample_w = max(40, int(image.width * 0.25))
    sample_h = max(20, int(image.height * 0.10))
    corner_crop = image.crop((margin_x, margin_y, min(image.width, margin_x + sample_w), min(image.height, margin_y + sample_h))).convert("L")
    pixels = list(corner_crop.getdata())
    avg_lum = sum(pixels) / len(pixels) if pixels else 255.0

    target_bytes = logo_dark_bytes if (avg_lum > 140 and logo_dark_bytes) else (logo_bytes or logo_dark_bytes)

    try:
        with Image.open(BytesIO(target_bytes)) as source_logo:
            logo = source_logo.convert("RGBA")
    except (ValueError, UnidentifiedImageError, OSError) as error:
        raise ImagePipelineError("The generated image or uploaded logo could not be composited.") from error
    if logo.width < 1 or logo.height < 1:
        raise ImagePipelineError("The generated image or uploaded logo has invalid dimensions.")

    max_width = max(80, int(image.width * 0.28))
    max_height = max(45, int(image.height * 0.12))
    scale = min(max_width / logo.width, max_height / logo.height, 1.0)
    logo = logo.resize((max(1, round(logo.width * scale)), max(1, round(logo.height * scale))), Image.Resampling.LANCZOS)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay.paste(logo, (margin_x, margin_y), logo)
    image = Image.alpha_composite(image, overlay)

    output = BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    branded = output.getvalue()
    if len(branded) > 20_000_000:
        raise ImagePipelineError("The corner-branded image is too large for upload.")
    return base64.b64encode(branded).decode("ascii")


async def _attach(client: httpx.AsyncClient, *, shopify_domain: str, shopify_token: str,
                  product_id: str, encoded: str, filename: str) -> dict:
    try:
        response = await client.post(
            f"https://{shopify_domain}/admin/api/{SHOPIFY_API_VERSION}/products/{product_id}/images.json",
            headers={"X-Shopify-Access-Token": shopify_token, "Content-Type": "application/json"},
            json={"image": {"attachment": encoded, "filename": filename}},
        )
    except httpx.RequestError as error:
        raise ImagePipelineError("The image pipeline could not reach Shopify.") from error
    if response.status_code not in (200, 201):
        raise ImagePipelineError(f"Shopify image upload failed (HTTP {response.status_code}).")
    try:
        uploaded = response.json()["image"]
        image_id = str(uploaded["id"])
        if not image_id.isdigit() or str(uploaded.get("product_id")) != product_id:
            raise ValueError("Unexpected Shopify image response")
    except (KeyError, TypeError, ValueError) as error:
        raise ImagePipelineError("Shopify did not confirm the product image upload.") from error
    return {"image_id": image_id, "product_id": product_id, "src": uploaded.get("src", "")}


async def generate_and_attach_images(
    *, gemini_key: str | list[str], shopify_domain: str, shopify_token: str, product_gid: str,
    source_image_urls: list[str], product_title: str, source_title: str, store_name: str,
    primary_color: str = "#2251dc", accent_color: str = "#6f9cff",
    brand_style: str = "", target_audience: str = "", product_facts: str = "",
    logo_mime: str = "", logo_bytes: bytes | None = None,
    logo_dark_mime: str = "", logo_dark_bytes: bytes | None = None,
    roles: tuple[str, ...] = IMAGE_ROLES, client: httpx.AsyncClient | None = None,
) -> list[dict]:
    keys = [gemini_key] if isinstance(gemini_key, str) else list(gemini_key)
    if not any(k and str(k).strip() for k in keys):
        raise ImagePipelineError("Gemini image generation is not configured.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", shopify_domain):
        raise ImagePipelineError("The Shopify store address is invalid.")
    match = re.fullmatch(r"gid://shopify/Product/([0-9]+)", product_gid)
    if not match:
        raise ImagePipelineError("The Shopify product ID is invalid.")
    if not source_image_urls:
        raise ImagePipelineError("A source product image is required.")
    if roles == IMAGE_ROLES and not logo_bytes and not logo_dark_bytes:
        raise ImagePipelineError("An uploaded PNG, JPEG, or WebP store logo is required for the branded gallery.")
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=120, follow_redirects=False, trust_env=False)
    try:
        references: list[tuple[str, bytes]] = []
        for url in source_image_urls[:len(roles)]:
            references.append(await _download_reference(client, url))
        results: list[dict] = []
        for index, role in enumerate(roles):
            source_mime, source_bytes = references[min(index, len(references) - 1)]
            prompt = _role_prompt(
                role, product_title=product_title, source_title=source_title,
                store_name=store_name, primary_color=primary_color,
                accent_color=accent_color, brand_style=brand_style,
                target_audience=target_audience, product_facts=product_facts,
            )
            encoded = await _generate_png(
                client, gemini_key=gemini_key, prompt=prompt,
                source_mime=source_mime, source_bytes=source_bytes,
                logo_mime=logo_mime, logo_bytes=logo_bytes,
                logo_dark_mime=logo_dark_mime, logo_dark_bytes=logo_dark_bytes,
            )
            if logo_bytes or logo_dark_bytes:
                encoded = _add_corner_logo(encoded, logo_bytes=logo_bytes, logo_dark_bytes=logo_dark_bytes)
            result = await _attach(
                client, shopify_domain=shopify_domain, shopify_token=shopify_token,
                product_id=match.group(1), encoded=encoded,
                filename=("ai-mockup.png" if roles == ("hero",) else f"4gmc-{role}.png"),
            )
            result["role"] = role
            result["corner_logo"] = bool(logo_bytes or logo_dark_bytes)
            result["product_logo_placements"] = "up_to_3_physical_surfaces"
            results.append(result)
        return results
    finally:
        if own_client:
            await client.aclose()


async def generate_and_attach_image(
    *, gemini_key: str, shopify_domain: str, shopify_token: str, product_gid: str,
    source_image_url: str, product_title: str, store_name: str,
    primary_color: str = "#2251dc", accent_color: str = "#6f9cff",
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Compatibility wrapper for a single hero image."""
    results = await generate_and_attach_images(
        gemini_key=gemini_key, shopify_domain=shopify_domain,
        shopify_token=shopify_token, product_gid=product_gid,
        source_image_urls=[source_image_url], product_title=product_title,
        source_title=product_title, store_name=store_name,
        primary_color=primary_color, accent_color=accent_color,
        roles=("hero",), client=client,
    )
    return results[0]
