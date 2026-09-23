"""Catalog-wide branding, curation, inventory, and GMC identifier rules for 4GMC."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from urllib.parse import urlparse

VALID_GTIN_LENGTHS = {8, 12, 13, 14}
EXCLUDED_TERMS = {
    "gift card", "gift-card", "store credit", "digital download",
    "subscription", "warranty",
}
IMAGE_ROLES = ("hero", "detail", "lifestyle")
MAX_PRODUCTS = 20
MAX_CATEGORIES = 4


def normalize_gtin(value: object) -> str:
    return re.sub(r"[\s-]", "", str(value or ""))


def calculate_check_digit(body: str) -> int:
    if not body.isdigit():
        raise ValueError("GTIN must contain digits only")
    total = sum(int(char) * (3 if offset % 2 == 0 else 1)
                for offset, char in enumerate(reversed(body)))
    return (10 - total % 10) % 10


def valid_gtin(value: object) -> bool:
    gtin = normalize_gtin(value)
    return (gtin.isdigit() and len(gtin) in VALID_GTIN_LENGTHS and
            calculate_check_digit(gtin[:-1]) == int(gtin[-1]))


def clean_category(value: object) -> str:
    category = " ".join(str(value or "").split()).strip()
    if not category or category.casefold() in {"product", "products", "other"}:
        return "Featured Products"
    return category[:80]


def is_physical_product(item: dict) -> bool:
    text = " ".join([
        str(item.get("title", "")), str(item.get("product_type", "")),
        str(item.get("type", "")), " ".join(map(str, item.get("tags", []) or [])),
    ]).casefold()
    return not any(term in text for term in EXCLUDED_TERMS)


def source_images(item: dict) -> list[str]:
    values = item.get("images", []) or []
    result: list[str] = []
    for image in values:
        value = image if isinstance(image, str) else image.get("src", "") if isinstance(image, dict) else ""
        if isinstance(value, str) and value.startswith("//"):
            value = "https:" + value
        elif isinstance(value, str) and value.startswith("http://"):
            value = "https://" + value[7:]
        parsed = urlparse(str(value))
        if parsed.scheme == "https" and parsed.hostname and value not in result:
            result.append(str(value))
    return result[:20]


def choose_variant(item: dict) -> dict:
    variants = [v for v in (item.get("variants") or []) if isinstance(v, dict)]
    if not variants:
        return {}
    available = [v for v in variants if v.get("available") is True]
    pool = available or variants
    with_image = [v for v in pool if v.get("featured_image") or v.get("image_id")]
    return dict((with_image or pool)[0])


def visual_score(item: dict) -> tuple[int, int, int, int]:
    variants = [v for v in (item.get("variants") or []) if isinstance(v, dict)]
    available = any(v.get("available") is True for v in variants)
    description = str(item.get("description") or item.get("body_html") or "")
    return (min(len(source_images(item)), 8), int(available), min(len(description), 2000), len(variants))


def curate_catalog(items: list[dict], max_products: int = MAX_PRODUCTS,
                   max_categories: int = MAX_CATEGORIES) -> list[dict]:
    """Choose a balanced physical catalog with one available variant per product."""
    candidates = [item for item in items if is_physical_product(item)] or list(items)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in candidates:
        category = clean_category(item.get("product_type") or item.get("type"))
        item = dict(item)
        item["_4gmc_category"] = category
        grouped[category].append(item)
    for values in grouped.values():
        values.sort(key=visual_score, reverse=True)
    categories = sorted(grouped, key=lambda name: (
        max((visual_score(item) for item in grouped[name]), default=(0, 0, 0, 0)),
        len(grouped[name]), name.casefold()), reverse=True)[:max(1, max_categories)]
    selected: list[dict] = []
    index = 0
    while len(selected) < max(1, max_products):
        added = False
        for category in categories:
            if index < len(grouped[category]):
                item = grouped[category][index]
                item["_4gmc_variant"] = choose_variant(item)
                selected.append(item)
                added = True
                if len(selected) >= max_products:
                    break
        if not added:
            break
        index += 1
    return selected


def stable_private_label_mpn(store_name: str, source_url: str, variant: dict) -> str:
    prefix = re.sub(r"[^A-Z0-9]", "", store_name.upper())[:12] or "STORE"
    basis = json.dumps([source_url, variant.get("id"), variant.get("sku"), variant.get("title")],
                       ensure_ascii=False, separators=(",", ":"))
    return f"{prefix}-{hashlib.sha256(basis.encode()).hexdigest()[:12].upper()}"


def stable_sku(store_name: str, source_url: str, variant: dict) -> str:
    prefix = re.sub(r"[^A-Z0-9]", "", store_name.upper())[:10] or "STORE"
    source_sku = re.sub(r"[^A-Za-z0-9_-]", "", str(variant.get("sku") or ""))[:28]
    basis = json.dumps([source_url, variant.get("id"), variant.get("title")], ensure_ascii=False)
    suffix = hashlib.sha256(basis.encode()).hexdigest()[:10].upper()
    return f"{prefix}-{source_sku + '-' if source_sku else ''}{suffix}"[:64]


def inventory_facts(variant: dict) -> tuple[bool, int | None, str]:
    for key in ("inventory_quantity", "quantity_available", "inventoryQuantity"):
        value = variant.get(key)
        if isinstance(value, int) and value >= 0:
            return True, value, "source_exact_quantity"
    if variant.get("available") is True:
        return False, None, "source_available_quantity_unknown"
    if variant.get("available") is False:
        return True, 0, "source_unavailable"
    return False, None, "source_availability_unknown"


def product_gmc_data(item: dict, store_name: str, source_url: str) -> dict:
    """Build truthful private-label identifier and inventory decisions.

    A source barcode is retained as a candidate for supplier confirmation. It is only
    used automatically when the source vendor already matches the destination brand.
    """
    variant = dict(item.get("_4gmc_variant") or choose_variant(item))
    vendor = " ".join(str(item.get("vendor") or "").split())
    candidate_gtin = normalize_gtin(variant.get("barcode"))
    same_brand = vendor.casefold() == store_name.strip().casefold() and bool(vendor)
    gtin = candidate_gtin if same_brand and valid_gtin(candidate_gtin) else ""
    mpn = "" if gtin else stable_private_label_mpn(store_name, source_url, variant)
    tracked, quantity, inventory_source = inventory_facts(variant)
    category = clean_category(item.get("_4gmc_category") or item.get("product_type") or item.get("type"))
    return {
        "brand": store_name.strip(),
        "condition": "new",
        "gtin": gtin,
        "mpn": mpn,
        "identifier_exists": True,
        "identifier_basis": "verified_source_gtin" if gtin else "private_label_brand_and_mpn",
        "source_gtin_candidate": candidate_gtin if candidate_gtin and not gtin else "",
        "source_gtin_candidate_valid": valid_gtin(candidate_gtin) if candidate_gtin else False,
        "source_vendor": vendor,
        "google_product_category": "",
        "google_category_strategy": "merchant_center_automatic",
        "product_type": category,
        "availability": "in_stock",
        "inventory_tracked": tracked,
        "inventory_quantity": quantity,
        "inventory_source": inventory_source,
        "selected_variant_id": str(variant.get("id") or ""),
        "selected_variant_title": str(variant.get("title") or ""),
        "sku": stable_sku(store_name, source_url, variant),
        "image_roles": list(IMAGE_ROLES),
        "rules_version": "2.0-realistic-bulk-catalog",
    }


def brand_fingerprint(store_name: str, brand: dict) -> str:
    canonical = {
        "name": store_name.strip(),
        "colors": [brand.get("color", ""), brand.get("accent", "")],
        "logo_digest": (brand.get("logo") or {}).get("digest", ""),
        "roles": list(IMAGE_ROLES),
        "policy": "2.1-corner-logo-multiposition",
    }
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_gmc_data(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("gtin") and not valid_gtin(data["gtin"]):
        errors.append("GTIN check digit or length is invalid")
    if data.get("identifier_exists") and not (data.get("gtin") or (data.get("brand") and data.get("mpn"))):
        errors.append("identifier_exists requires a verified GTIN or both brand and MPN")
    if not data.get("sku"):
        errors.append("SKU is missing")
    if data.get("availability") not in {"in_stock", "out_of_stock", "preorder", "backorder"}:
        errors.append("Availability is invalid")
    if not data.get("product_type"):
        errors.append("Product type is missing")
    return errors
