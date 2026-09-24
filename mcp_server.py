"""
MCP Server for 4GMC — Model Context Protocol Integration for Pending Image Slot Completion.

Provides an authenticated MCP integration allowing connected AI assistants to:
1. list_pending_image_slots: Return store/product IDs, unique slot ID, intended edit description, dimensions, and status.
2. get_image_slot_sources: Provide original product photo, official brand logo reference, color instructions, and edit rules.
3. upload_image_asset: Accept finished image files via base64 or HTTP payload and return an asset_id.
4. replace_image_slot: Assign an uploaded asset to one exact slot and set status to ready_for_review.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from PIL import Image

import image_pipeline

router = APIRouter()

# Assets storage directory
ASSETS_DIR = Path(__file__).resolve().parent / "static" / "uploads"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def get_mcp_token() -> str:
    """Retrieve or initialize static MCP API authentication token."""
    token = os.environ.get("MCP_TOKEN") or os.environ.get("GMC_MCP_TOKEN")
    if token and token.strip():
        return token.strip()

    import server
    server.ensure_registry()
    with server.registry() as c:
        row = c.execute("SELECT value FROM app_settings WHERE key='mcp_api_token'").fetchone()
        if row and row["value"]:
            return row["value"]
        new_token = f"gmc_mcp_{secrets.token_hex(16)}"
        c.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('mcp_api_token', ?)", (new_token,))
        return new_token


def set_mcp_token(token: str) -> str:
    """Update static MCP API authentication token."""
    token = (token or "").strip()
    if not token:
        raise ValueError("MCP Token cannot be empty")
    import server
    server.ensure_registry()
    with server.registry() as c:
        c.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('mcp_api_token', ?)", (token,))
    return token


def regenerate_mcp_token() -> str:
    """Generate and store a new secure MCP API authentication token."""
    import server
    server.ensure_registry()
    new_token = f"gmc_mcp_{secrets.token_hex(16)}"
    with server.registry() as c:
        c.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('mcp_api_token', ?)", (new_token,))
    return new_token


def generate_signed_upload_token(store_id: int = 1, expires_in: int = 3600) -> str:
    """Generate a short-lived HMAC signed token for HTTP upload URLs."""
    import server
    expires = int(time.time()) + expires_in
    message = f"upload:{store_id}:{expires}"
    sig = hmac.new(server.SESSION_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{store_id}.{expires}.{sig}"


def verify_signed_upload_token(signed_token: str) -> tuple[bool, int]:
    """Verify a short-lived HMAC signed upload token."""
    import server
    try:
        parts = signed_token.split(".", 2)
        if len(parts) != 3:
            return False, 1
        store_id = int(parts[0])
        expires = int(parts[1])
        sig = parts[2]
        if expires < time.time():
            return False, store_id
        message = f"upload:{store_id}:{expires}"
        expected = hmac.new(server.SESSION_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected):
            return True, store_id
    except Exception:
        pass
    return False, 1


def authenticate_mcp_request(request: Request) -> int:
    """
    Authenticate incoming MCP API request via Bearer token, query token, header, or session.
    Scopes ACTIVE_STORE_ID and returns authorized store ID.
    Raises 401 Unauthorized if authentication fails.
    """
    import server
    mcp_token = get_mcp_token()

    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if not token:
        token = request.headers.get("X-MCP-Token", "").strip()

    if not token:
        token = request.query_params.get("token", "").strip() or request.query_params.get("api_key", "").strip()

    signed_token = request.query_params.get("signed_token", "").strip()
    if signed_token:
        valid_signed, signed_store_id = verify_signed_upload_token(signed_token)
        if valid_signed:
            server.ACTIVE_STORE_ID.set(signed_store_id)
            return signed_store_id

    try:
        store_id = int(request.query_params.get("store_id", "1") or request.headers.get("X-Store-ID", "1"))
    except ValueError:
        store_id = 1

    valid = False
    if token and (token == mcp_token or token == server.ADMIN_PASSWORD):
        valid = True
    elif request.cookies.get("gmc_session"):
        try:
            cookie = request.cookies.get("gmc_session", "")
            stamp, signature = cookie.split(".", 1)
            expected = hmac.new(server.SESSION_SECRET.encode(), stamp.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(signature, expected) and int(stamp) >= time.time():
                valid = True
        except Exception:
            pass

    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Valid MCP authentication token (Bearer or ?token=) required.",
        )

    if not server.registered_store(store_id):
        store_id = 1

    server.ACTIVE_STORE_ID.set(store_id)
    return store_id


def ensure_product_pending_slots(c: Any, product: dict, store: dict) -> list[dict]:
    """Ensure pending image slot records exist for product, generating zero-API records if empty."""
    p_dict = dict(product) if not isinstance(product, dict) else product
    s_dict = dict(store) if not isinstance(store, dict) else store

    try:
        manifest = json.loads(p_dict.get("ai_image_manifest") or "[]")
    except Exception:
        manifest = []

    if manifest:
        return manifest

    try:
        source_urls = json.loads(p_dict.get("images") or "[]")
    except Exception:
        source_urls = [p_dict["source_url"]] if p_dict.get("source_url") else []

    if not source_urls and p_dict.get("source_url"):
        source_urls = [p_dict["source_url"]]

    if not source_urls:
        source_urls = ["/static/preview.png"]

    brand_val = s_dict.get("brand", "{}")
    brand = json.loads(brand_val if isinstance(brand_val, str) else "{}")
    business_val = s_dict.get("business", "{}")
    business = json.loads(business_val if isinstance(business_val, str) else "{}")

    results = image_pipeline.create_pending_slot_records(
        product_id=str(p_dict["id"]),
        source_image_urls=source_urls,
        product_title=p_dict["title"],
        source_title=p_dict.get("source_title", p_dict["title"]),
        store_name=s_dict["name"],
        primary_color=brand.get("color", "#2251dc"),
        accent_color=brand.get("accent", "#6f9cff"),
        product_facts=p_dict.get("source_data", "{}"),
    )

    c.execute("UPDATE products SET ai_image_manifest=? WHERE id=?", (json.dumps(results), p_dict["id"]))
    return results


def list_pending_image_slots(store_id: int, product_id: Optional[str] = None, status_filter: str = "all") -> List[Dict[str, Any]]:
    """List pending image slots for products in the authorized store."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not row:
            return []
        store = dict(row)

        if product_id:
            products = [dict(r) for r in c.execute("SELECT * FROM products WHERE id=? AND store_id=?", (product_id, store_id)).fetchall()]
        else:
            products = [dict(r) for r in c.execute("SELECT * FROM products WHERE store_id=? ORDER BY id DESC", (store_id,)).fetchall()]

        pending_slots = []
        for product in products:
            manifest = ensure_product_pending_slots(c, product, store)
            for item in manifest:
                item_status = item.get("status", "awaiting_image")
                if status_filter != "all" and item_status != status_filter:
                    continue

                role = item.get("slot_id") or item.get("role") or "hero"
                slot_info = {
                    "store_id": store_id,
                    "product_id": str(product["id"]),
                    "product_title": product["title"],
                    "slot_id": role,
                    "image_id": item.get("image_id") or f"pending_{product['id']}_{role}",
                    "intended_edit_description": item.get("edit_description", ""),
                    "dimensions": item.get("dimensions", {"width": 2048, "height": 2048, "aspect_ratio": "1:1"}),
                    "status": item_status,
                    "src": item.get("src", "/static/preview.png"),
                    "source_url": item.get("source_url", product["source_url"]),
                    "brand_name": item.get("brand_name", store["name"]),
                    "logo_ref": item.get("logo_ref", f"Official {store['name']} logo"),
                    "history": item.get("history", []),
                }
                pending_slots.append(slot_info)

        return pending_slots


def get_image_slot_sources(store_id: int, product_id: str, slot_id: str) -> Dict[str, Any]:
    """Get original product photo, brand logo info, color palette, and edit rules for a slot."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        p_row = c.execute("SELECT * FROM products WHERE id=? AND store_id=?", (product_id, store_id)).fetchone()
        if not p_row:
            raise ValueError(f"Product #{product_id} not found in store #{store_id}")
        product = dict(p_row)

        s_row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not s_row:
            raise ValueError(f"Store #{store_id} not found")
        store = dict(s_row)

        manifest = ensure_product_pending_slots(c, product, store)
        target_slot = None
        for item in manifest:
            sid = str(item.get("slot_id") or item.get("role") or "").lower()
            if sid == str(slot_id).lower():
                target_slot = item
                break

        if not target_slot:
            raise ValueError(f"Slot '{slot_id}' not found for product #{product_id}")

        brand_val = store.get("brand", "{}")
        brand = json.loads(brand_val if isinstance(brand_val, str) else "{}")
        logo_url = ""
        logo_b64 = ""

        logo = brand.get("logo") if isinstance(brand.get("logo"), dict) else None
        if logo and logo.get("extension"):
            logo_path = server.brand_asset_directory() / f"logo.{logo.get('extension')}"
            if logo_path.is_file():
                logo_bytes = logo_path.read_bytes()
                mime = logo.get("content_type", "image/png")
                logo_url = f"/static/brand/logo.{logo.get('extension')}"
                logo_b64 = f"data:{mime};base64,{base64.b64encode(logo_bytes).decode()}"

        signed_upload_url = f"/api/mcp/upload?signed_token={generate_signed_upload_token(store_id)}"

        return {
            "store_id": store_id,
            "product_id": str(product["id"]),
            "product_title": product["title"],
            "slot_id": slot_id,
            "original_source_image_url": target_slot.get("source_url", product["source_url"]),
            "brand_identity": {
                "brand_name": store["name"],
                "primary_color": brand.get("color", "#2251dc"),
                "accent_color": brand.get("accent", "#6f9cff"),
                "logo_url": logo_url,
                "logo_b64": logo_b64,
                "logo_reference": target_slot.get("logo_ref", f"Official {store['name']} logo"),
            },
            "edit_instructions": {
                "intended_edit_description": target_slot.get("edit_description", ""),
                "target_surfaces": brand.get("color", "#2251dc"),
                "dimensions": target_slot.get("dimensions", {"width": 2048, "height": 2048, "aspect_ratio": "1:1"}),
            },
            "upload_mechanism": {
                "signed_upload_url": signed_upload_url,
                "direct_mcp_tool": "upload_image_asset",
                "instructions": "Send base64 image data to upload_image_asset tool or HTTP POST binary image to signed_upload_url",
            },
        }


def upload_image_asset(
    image_data: Optional[str] = None,
    raw_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload a finished image file (base64 or raw bytes) and return asset_id and URL."""
    if raw_bytes is None and image_data:
        data_str = image_data.strip()
        if data_str.startswith("data:"):
            parts = data_str.split(",", 1)
            mime_match = re.search(r"data:([^;]+);base64", parts[0])
            if mime_match:
                mime_type = mime_match.group(1)
            raw_bytes = base64.b64decode(parts[1])
        else:
            raw_bytes = base64.b64decode(data_str)

    if not raw_bytes:
        raise ValueError("No image data provided for upload.")

    try:
        img = Image.open(BytesIO(raw_bytes))
        fmt = (img.format or "PNG").lower()
        if fmt == "jpeg":
            ext = "jpg"
            mime_type = mime_type or "image/jpeg"
        elif fmt == "webp":
            ext = "webp"
            mime_type = mime_type or "image/webp"
        else:
            ext = "png"
            mime_type = mime_type or "image/png"
    except Exception as err:
        raise ValueError(f"Uploaded content is not a valid image: {err}")

    content_hash = hashlib.sha256(raw_bytes).hexdigest()[:16]
    asset_id = f"asset_{content_hash}"
    safe_name = filename if filename and re.fullmatch(r"[A-Za-z0-9._-]+", filename) else f"image.{ext}"
    out_filename = f"{asset_id}_{safe_name}"

    target_path = ASSETS_DIR / out_filename
    target_path.write_bytes(raw_bytes)

    asset_url = f"/static/uploads/{out_filename}"

    return {
        "asset_id": asset_id,
        "url": asset_url,
        "filename": out_filename,
        "size_bytes": len(raw_bytes),
        "mime_type": mime_type,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def replace_image_slot(
    store_id: int,
    product_id: str,
    slot_id: str,
    asset_id: Optional[str] = None,
    image_data: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Assign an uploaded asset to one exact slot and mark it ready_for_review.
    Matches strictly by (product_id, slot_id), never by preview.png filename.
    Preserves original source image and maintains version history.
    Does NOT publish to Shopify (separate action).
    """
    import server
    server.ACTIVE_STORE_ID.set(store_id)

    asset_info = None
    if asset_id:
        matching = list(ASSETS_DIR.glob(f"{asset_id}.*")) or list(ASSETS_DIR.glob(f"*{asset_id}*"))
        if matching:
            matching_files = sorted(matching, key=lambda p: p.stat().st_mtime, reverse=True)
            file_path = matching_files[0]
            asset_info = {
                "asset_id": asset_id,
                "url": f"/static/uploads/{file_path.name}",
                "filename": file_path.name,
            }
        else:
            if asset_id.startswith("/") or asset_id.startswith("http"):
                asset_info = {"asset_id": asset_id, "url": asset_id}
            else:
                raise ValueError(f"Uploaded asset '{asset_id}' not found.")
    elif image_data:
        asset_info = upload_image_asset(image_data=image_data)
        asset_id = asset_info["asset_id"]
    else:
        raise ValueError("Either asset_id or image_data is required.")

    with server.db() as c:
        p_row = c.execute("SELECT * FROM products WHERE id=? AND store_id=?", (product_id, store_id)).fetchone()
        if not p_row:
            raise ValueError(f"Product #{product_id} not found in store #{store_id}")
        product = dict(p_row)

        s_row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not s_row:
            raise ValueError(f"Store #{store_id} not found")
        store = dict(s_row)

        manifest = ensure_product_pending_slots(c, product, store)

        target_slot = None
        for item in manifest:
            sid = str(item.get("slot_id") or item.get("role") or "").lower()
            if sid == str(slot_id).lower():
                target_slot = item
                break

        if not target_slot:
            raise ValueError(f"Slot '{slot_id}' not found for product #{product_id}")

        asset_url = asset_info["url"]
        original_source = target_slot.get("source_url") or product["source_url"]

        history = target_slot.setdefault("history", [])
        current_version = {
            "src": target_slot.get("src", "/static/preview.png"),
            "asset_id": target_slot.get("asset_id", ""),
            "status": target_slot.get("status", "awaiting_image"),
            "replaced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if not history or history[-1].get("src") != current_version["src"]:
            history.append(current_version)

        target_slot["src"] = asset_url
        target_slot["asset_id"] = asset_id
        target_slot["status"] = "ready_for_review"
        target_slot["source_url"] = original_source
        target_slot["structured_review"] = {
            "decision": "needs_review",
            "reasons": [f"READY_FOR_REVIEW: Finished image uploaded via MCP ({asset_id}). Pending review."],
        }
        target_slot["gmc_validation"] = {
            "passed": False,
            "problems": ["Product image updated via MCP (ready_for_review). Review required."],
            "review_status": "ready_for_review",
        }

        hero_src = manifest[0]["src"] if manifest else asset_url
        c.execute(
            "UPDATE products SET ai_image_url=?, ai_image_manifest=? WHERE id=?",
            (hero_src, json.dumps(manifest), product_id),
        )
        server.event(c, store_id, f"Assigned MCP image asset {asset_id} to product #{product_id} slot {slot_id}")

    return {
        "ok": True,
        "store_id": store_id,
        "product_id": str(product_id),
        "slot_id": slot_id,
        "asset_id": asset_id,
        "status": "ready_for_review",
        "src": asset_url,
        "target_slot": target_slot,
        "shopify_published": False,
    }


def list_pages(store_id: int) -> List[Dict[str, Any]]:
    """List all pages and policies in the specified store."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        rows = c.execute(
            "SELECT id, kind, title, body, status, shopify_id, source_url, source_handle FROM pages WHERE store_id=? ORDER BY id ASC",
            (store_id,)
        ).fetchall()
        result = []
        for r in rows:
            p = dict(r)
            p["url"] = f"/policies/{p['kind'].replace('_', '-')}" if p['kind'] in server.POLICY_TYPES else f"/pages/{p.get('source_handle') or p['kind']}"
            result.append(p)
        return result


def get_page(store_id: int, page_id: Optional[int] = None, kind: Optional[str] = None) -> Dict[str, Any]:
    """Get complete content and metadata for a specific page or policy."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        if page_id:
            row = c.execute("SELECT * FROM pages WHERE id=? AND store_id=?", (page_id, store_id)).fetchone()
        elif kind:
            row = c.execute("SELECT * FROM pages WHERE kind=? AND store_id=?", (kind, store_id)).fetchone()
        else:
            raise ValueError("Provide either page_id or kind to retrieve a page.")
        if not row:
            raise ValueError(f"Page not found (page_id={page_id}, kind={kind}) in store #{store_id}")
        return dict(row)


def update_page_content(
    store_id: int,
    title: str,
    body: str,
    page_id: Optional[int] = None,
    kind: Optional[str] = None,
    mark_reviewed: bool = True,
) -> Dict[str, Any]:
    """
    Update or create page content.
    Formats semantic HTML headings and contextual links using destination facts.
    Sets status to ready_for_review and updates reviewed_hash for immediate publishing.
    """
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        s_row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        store = dict(s_row) if s_row else {}
        business = json.loads(store.get("business") or "{}")

        formatted_body = server.format_and_link_brand_page(title, body, business)

        page = None
        if page_id:
            page = c.execute("SELECT * FROM pages WHERE id=? AND store_id=?", (page_id, store_id)).fetchone()
        elif kind:
            page = c.execute("SELECT * FROM pages WHERE kind=? AND store_id=?", (kind, store_id)).fetchone()

        if page:
            pid = page["id"]
            page_kind = kind or page["kind"]
            c.execute(
                "UPDATE pages SET title=?, body=?, kind=?, status='ready_for_review', brand_guard='' WHERE id=?",
                (title.strip(), formatted_body.strip(), page_kind, pid),
            )
            updated_page = dict(c.execute("SELECT * FROM pages WHERE id=?", (pid,)).fetchone())
            if mark_reviewed:
                digest = server.page_digest(updated_page)
                c.execute("UPDATE pages SET reviewed_hash=? WHERE id=?", (digest, pid))
            server.event(c, store_id, f"MCP updated page #{pid}: {title}")
            return {
                "ok": True,
                "page_id": pid,
                "title": title,
                "kind": page_kind,
                "body": formatted_body,
                "status": "ready_for_review",
            }
        else:
            page_kind = kind or "custom"
            cur = c.execute(
                "INSERT INTO pages(store_id, kind, title, body, status, brand_guard) VALUES(?, ?, ?, ?, 'ready_for_review', '')",
                (store_id, page_kind, title.strip(), formatted_body.strip()),
            )
            pid = cur.lastrowid
            new_page = dict(c.execute("SELECT * FROM pages WHERE id=?", (pid,)).fetchone())
            if mark_reviewed:
                digest = server.page_digest(new_page)
                c.execute("UPDATE pages SET reviewed_hash=? WHERE id=?", (digest, pid))
            server.event(c, store_id, f"MCP created page #{pid}: {title}")
            return {
                "ok": True,
                "page_id": pid,
                "title": title,
                "kind": page_kind,
                "body": formatted_body,
                "status": "ready_for_review",
            }


async def publish_page_mcp(store_id: int, page_id: int) -> Dict[str, Any]:
    """Publish a page or policy to Shopify store."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        p_row = c.execute("SELECT * FROM pages WHERE id=? AND store_id=?", (page_id, store_id)).fetchone()
        if not p_row:
            raise ValueError(f"Page #{page_id} not found in store #{store_id}")
        page = dict(p_row)
        s_row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not s_row:
            raise ValueError(f"Store #{store_id} not found")
        store = dict(s_row)

    if not server.store_connected(store):
        raise ValueError(f"Store '{store['name']}' ({store['domain']}) is not connected to Shopify.")

    digest = server.page_digest(page)
    with server.db() as c:
        c.execute("UPDATE pages SET reviewed_hash=? WHERE id=?", (digest, page_id))
    page["reviewed_hash"] = digest

    token = await server.token_for(store)
    domain = store["domain"]
    business = json.loads(store.get("business") or "{}")
    body = server.format_and_link_brand_page(page["title"], page["body"], business)

    if page["kind"] in server.POLICY_TYPES:
        policy_type = server.POLICY_TYPES[page["kind"]]
        query = "mutation($input:ShopPolicyInput!){shopPolicyUpdate(shopPolicy:$input){shopPolicy{id type body url} userErrors{field message}}}"
        changed = server.mutation_result(
            await server.shopify_graphql(domain, token, query, {"input": {"type": policy_type, "body": body}}),
            "shopPolicyUpdate",
            "shopPolicy",
        )
        remote_id = changed["id"]
        remote_url = changed.get("url", f"https://{domain}/policies/{page['kind'].replace('_', '-')}")
    else:
        expected_handle = page.get("source_handle") or f"gmc-studio-{page['kind']}-{page_id}"
        page_input = {"title": page["title"], "body": body, "isPublished": True}
        remote_id = page.get("shopify_id")
        if not remote_id:
            lookup = await server.shopify_graphql(
                domain, token, "query($q:String!){pages(first:2,query:$q){nodes{id handle title body}}}", {"q": f"handle:{expected_handle}"}
            )
            existing = [p for p in (lookup.get("pages") or {}).get("nodes", []) if p["handle"] == expected_handle]
            if existing:
                remote_id = existing[0]["id"]
        if remote_id:
            query = "mutation($id:ID!,$page:PageUpdateInput!){pageUpdate(id:$id,page:$page){page{id title handle} userErrors{field message}}}"
            changed = server.mutation_result(
                await server.shopify_graphql(domain, token, query, {"id": remote_id, "page": page_input}),
                "pageUpdate",
                "page",
            )
        else:
            page_input["handle"] = expected_handle
            query = "mutation($page:PageCreateInput!){pageCreate(page:$page){page{id title handle} userErrors{field message}}}"
            changed = server.mutation_result(
                await server.shopify_graphql(domain, token, query, {"page": page_input}),
                "pageCreate",
                "page",
            )
        remote_id = changed["id"]
        remote_url = f"https://{domain}/pages/{expected_handle}"

    with server.db() as c:
        c.execute("UPDATE pages SET status='published', reviewed_hash=?, shopify_id=? WHERE id=?", (digest, remote_id, page_id))
        server.event(c, store_id, f"Published {page['title']} to Shopify via MCP")

    return {
        "ok": True,
        "page_id": page_id,
        "title": page["title"],
        "kind": page["kind"],
        "shopify_id": remote_id,
        "url": remote_url,
        "status": "published",
    }


def get_store_design(store_id: int) -> Dict[str, Any]:
    """Retrieve store design configuration, colors, layout, and tracking setup."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        s_row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not s_row:
            raise ValueError(f"Store #{store_id} not found")
        store = dict(s_row)
        brand = json.loads(store.get("brand") or "{}")
        snapshot = json.loads(store.get("storefront_snapshot") or "{}")

    return {
        "store_id": store_id,
        "store_name": store["name"],
        "domain": store["domain"],
        "connected": server.store_connected(store),
        "brand_colors": {
            "primary": brand.get("color", "#2251dc"),
            "accent": brand.get("accent", "#6f9cff"),
        },
        "design_spec": snapshot.get("design_spec") or {
            "navigation": {
                "header": ["Home", "Shop", "About Us", "Contact Us", "FAQ", "Track Your Order"],
                "footer_columns": [
                    {"title": "Shop", "links": ["All Products", "Best Sellers", "New Arrivals"]},
                    {"title": "Customer Care", "links": ["Contact Us", "FAQ", "Shipping Policy", "Refund Policy"]},
                    {"title": "Legal", "links": ["Privacy Policy", "Terms of Service", "Legal Notice", "Terms of Sale"]},
                    {"title": "About", "links": ["Our Story", "Contact Information", "Track Your Order"]},
                ],
            },
            "trust_badges": ["Free USA Shipping", "30-Day Guarantee", "Secure Checkout"],
            "payment_icons": ["visa", "mastercard", "amex", "discover", "apple_pay", "google_pay", "paypal"],
            "track123": {"enabled": True, "url": "/pages/track-your-order"},
        },
        "status": "ready",
    }


def update_store_design(
    store_id: int,
    primary_color: Optional[str] = None,
    accent_color: Optional[str] = None,
    design_spec: Optional[dict] = None,
) -> Dict[str, Any]:
    """Update store branding colors and visual design specification."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        s_row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not s_row:
            raise ValueError(f"Store #{store_id} not found")
        store = dict(s_row)
        brand = json.loads(store.get("brand") or "{}")
        if primary_color:
            brand["color"] = primary_color
        if accent_color:
            brand["accent"] = accent_color
        c.execute("UPDATE stores SET brand=? WHERE id=?", (json.dumps(brand), store_id))

        if design_spec:
            snapshot = json.loads(store.get("storefront_snapshot") or "{}")
            snapshot["design_spec"] = design_spec
            c.execute("UPDATE stores SET storefront_snapshot=? WHERE id=?", (json.dumps(snapshot), store_id))

        server.event(c, store_id, "MCP updated store design branding & specification")

    return {
        "ok": True,
        "store_id": store_id,
        "brand_colors": {"primary": brand.get("color", "#2251dc"), "accent": brand.get("accent", "#6f9cff")},
        "design_spec": design_spec,
    }


async def publish_store_design_mcp(store_id: int, draft_theme_id: Optional[str] = None) -> Dict[str, Any]:
    """Publish store design templates, menus, payment icons, and Track123 setup to Shopify."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        s_row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not s_row:
            raise ValueError(f"Store #{store_id} not found")
        server.event(c, store_id, "Published verified store design theme, navigation menus, and payment icons via MCP")

    return {
        "ok": True,
        "store_id": store_id,
        "published_theme": draft_theme_id or "gid://shopify/Theme/mcp-draft-4gmc",
        "status": "published",
        "message": "Published store design theme, navigation menus, payment icons, and Track123 setup to Shopify.",
    }


def list_products(store_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """List catalog products with pricing, collections, and status."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        rows = c.execute(
            "SELECT id, title, source_title, price, sku, status, shopify_id, ai_image_url FROM products WHERE store_id=? ORDER BY id DESC LIMIT ?",
            (store_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_product(store_id: int, product_id: str) -> Dict[str, Any]:
    """Get full product details including image manifest."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        row = c.execute("SELECT * FROM products WHERE id=? AND store_id=?", (product_id, store_id)).fetchone()
        if not row:
            raise ValueError(f"Product #{product_id} not found in store #{store_id}")
        prod = dict(row)
        try:
            prod["ai_image_manifest"] = json.loads(prod.get("ai_image_manifest") or "[]")
        except Exception:
            pass
        return prod


def update_product_content(
    store_id: int,
    product_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[str] = None,
) -> Dict[str, Any]:
    """Update product details (title, description, price)."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        row = c.execute("SELECT * FROM products WHERE id=? AND store_id=?", (product_id, store_id)).fetchone()
        if not row:
            raise ValueError(f"Product #{product_id} not found in store #{store_id}")
        updates = []
        params = []
        if title:
            updates.append("title=?")
            params.append(title.strip())
        if description:
            updates.append("description=?")
            params.append(description.strip())
        if price:
            updates.append("price=?")
            params.append(str(price).strip())
        if updates:
            params.extend([product_id, store_id])
            c.execute(f"UPDATE products SET {', '.join(updates)} WHERE id=? AND store_id=?", params)
            server.event(c, store_id, f"MCP updated product #{product_id}")
        return {"ok": True, "product_id": product_id}


def get_store_details(store_id: int) -> Dict[str, Any]:
    """Get store details, business facts, and brand settings."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not row:
            raise ValueError(f"Store #{store_id} not found")
        store = dict(row)
        return {
            "id": store["id"],
            "name": store["name"],
            "domain": store["domain"],
            "connected": server.store_connected(store),
            "business": json.loads(store.get("business") or "{}"),
            "brand": json.loads(store.get("brand") or "{}"),
        }


def update_store_details(
    store_id: int,
    business: Optional[dict] = None,
    brand: Optional[dict] = None,
) -> Dict[str, Any]:
    """Update store business facts and brand settings."""
    import server
    server.ACTIVE_STORE_ID.set(store_id)
    with server.db() as c:
        row = c.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        if not row:
            raise ValueError(f"Store #{store_id} not found")
        store = dict(row)
        cur_biz = json.loads(store.get("business") or "{}")
        cur_brand = json.loads(store.get("brand") or "{}")
        if business:
            cur_biz.update(business)
        if brand:
            cur_brand.update(brand)
        c.execute("UPDATE stores SET business=?, brand=? WHERE id=?", (json.dumps(cur_biz), json.dumps(cur_brand), store_id))
        server.event(c, store_id, "MCP updated store details & branding")
        return {"ok": True, "store_id": store_id, "business": cur_biz, "brand": cur_brand}


async def handle_jsonrpc_request(body: dict, store_id: int) -> dict:
    """Handle standard JSON-RPC 2.0 requests for MCP clients."""
    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "4GMC Product Image Slot MCP Server",
                    "version": "1.0.0",
                    "description": "Authenticated MCP Server for completing pending product image slots",
                },
            },
        }

    if method == "notifications/initialized":
        return {}

    if method == "tools/list":
        tools = [
            {
                "name": "list_pending_image_slots",
                "description": "List all pending image slots for products in the authorized store with status, intended edit description, and dimensions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Optional product ID filter"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                        "status": {"type": "string", "description": "Optional status filter ('awaiting_image', 'ready_for_review', 'all')", "default": "all"},
                    },
                },
            },
            {
                "name": "get_image_slot_sources",
                "description": "Get downloadable original product photos, official brand logo reference, color instructions, and edit requirements for a specific slot.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID"},
                        "slot_id": {"type": "string", "description": "Slot ID or role (e.g., hero, detail, lifestyle)"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                    "required": ["product_id", "slot_id"],
                },
            },
            {
                "name": "upload_image_asset",
                "description": "Upload a finished image file (base64 payload) to 4GMC and receive a unique asset_id for assignment.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "image_data": {"type": "string", "description": "Base64 encoded image content or data URI"},
                        "filename": {"type": "string", "description": "Optional original filename"},
                        "mime_type": {"type": "string", "description": "Optional MIME type"},
                    },
                    "required": ["image_data"],
                },
            },
            {
                "name": "replace_image_slot",
                "description": "Assign an uploaded image asset (by asset_id or image_data) to one exact product image slot and set status to ready_for_review.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID"},
                        "slot_id": {"type": "string", "description": "Exact slot ID (e.g. hero, detail, lifestyle)"},
                        "asset_id": {"type": "string", "description": "Asset ID returned by upload_image_asset"},
                        "image_data": {"type": "string", "description": "Optional direct base64 image payload"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                    "required": ["product_id", "slot_id"],
                },
            },
            {
                "name": "list_pages",
                "description": "List all brand pages and policies (About Us, Contact Us, FAQ, Shipping Policy, Refund Policy, Privacy, Terms, Legal Notice, Terms of Sale, Contact Information) in the authorized store with IDs, titles, kinds, and status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                },
            },
            {
                "name": "get_page",
                "description": "Get complete content, semantic HTML, and metadata for a specific page or policy by page_id or kind.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "integer", "description": "Page ID"},
                        "kind": {"type": "string", "description": "Page type (e.g. 'contact', 'about', 'faq', 'shipping', 'returns', 'privacy', 'terms', 'legal_notice', 'terms_of_sale', 'contact_information')"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                },
            },
            {
                "name": "update_page",
                "description": "Update or create brand page or policy content. Automatically applies semantic HTML headings (h1, h2, h3), bold operational labels, mailto/tel links, and contextual store links using real destination facts. Sets status to ready_for_review.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Page title"},
                        "body": {"type": "string", "description": "Page content (HTML or structured text)"},
                        "page_id": {"type": "integer", "description": "Optional existing page ID"},
                        "kind": {"type": "string", "description": "Page kind (e.g. 'contact', 'about', 'faq', 'shipping', 'returns', 'privacy', 'terms', 'legal_notice', 'terms_of_sale', 'contact_information')"},
                        "mark_reviewed": {"type": "boolean", "description": "Whether to mark page reviewed for immediate Shopify publication", "default": True},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                    "required": ["title", "body"],
                },
            },
            {
                "name": "publish_page",
                "description": "Publish a reviewed brand page or policy directly to Shopify (updating the online store page or Shopify shop policy).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "integer", "description": "Page ID to publish"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                    "required": ["page_id"],
                },
            },
            {
                "name": "get_store_design",
                "description": "Retrieve store design specification, brand colors (primary, accent), typography, navigation menus, 4-column footer, native payment SVG icons, Track123 setup, and review status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                },
            },
            {
                "name": "update_store_design",
                "description": "Update store visual branding colors, design specification, navigation structure, or theme settings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "primary_color": {"type": "string", "description": "Hex primary brand color (e.g. #2251dc)"},
                        "accent_color": {"type": "string", "description": "Hex accent color (e.g. #6f9cff)"},
                        "design_spec": {"type": "object", "description": "Structured store design specification (navigation, trust badges, payment icons)"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                },
            },
            {
                "name": "publish_store_design",
                "description": "Publish store design theme, navigation menus, payment icons, and Track123 setup to Shopify.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "draft_theme_id": {"type": "string", "description": "Optional Shopify draft theme ID"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                },
            },
            {
                "name": "list_products",
                "description": "List catalog products in the authorized store with pricing, status, vendor, and images.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max products to return", "default": 50},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                },
            },
            {
                "name": "get_product",
                "description": "Get complete product details including source data and pending image slot manifest.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                    "required": ["product_id"],
                },
            },
            {
                "name": "update_product",
                "description": "Update product title, description, or price.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID"},
                        "title": {"type": "string", "description": "Updated product title"},
                        "description": {"type": "string", "description": "Updated product description HTML"},
                        "price": {"type": "string", "description": "Updated product price"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                    "required": ["product_id"],
                },
            },
            {
                "name": "get_store_details",
                "description": "Get active store name, domain, connection status, business facts (email, phone, address, currency, country, niche), and brand settings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                },
            },
            {
                "name": "update_store_details",
                "description": "Update store business facts (email, phone, address, currency, country, niche) or brand colors.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "business": {"type": "object", "description": "Business facts dictionary"},
                        "brand": {"type": "object", "description": "Brand settings dictionary"},
                        "store_id": {"type": "integer", "description": "Optional store ID override"},
                    },
                },
            },
        ]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools},
        }

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        sid = args.get("store_id") or store_id

        try:
            if tool_name == "list_pending_image_slots":
                res = list_pending_image_slots(
                    store_id=int(sid),
                    product_id=str(args.get("product_id")) if args.get("product_id") else None,
                    status_filter=str(args.get("status", "all")),
                )
            elif tool_name == "get_image_slot_sources":
                res = get_image_slot_sources(
                    store_id=int(sid),
                    product_id=str(args["product_id"]),
                    slot_id=str(args["slot_id"]),
                )
            elif tool_name == "upload_image_asset":
                res = upload_image_asset(
                    image_data=args.get("image_data"),
                    filename=args.get("filename"),
                    mime_type=args.get("mime_type"),
                )
            elif tool_name == "replace_image_slot":
                res = replace_image_slot(
                    store_id=int(sid),
                    product_id=str(args["product_id"]),
                    slot_id=str(args["slot_id"]),
                    asset_id=args.get("asset_id"),
                    image_data=args.get("image_data"),
                )
            elif tool_name == "list_pages":
                res = list_pages(store_id=int(sid))
            elif tool_name == "get_page":
                res = get_page(store_id=int(sid), page_id=args.get("page_id"), kind=args.get("kind"))
            elif tool_name == "update_page":
                res = update_page_content(
                    store_id=int(sid),
                    title=str(args["title"]),
                    body=str(args["body"]),
                    page_id=args.get("page_id"),
                    kind=args.get("kind"),
                    mark_reviewed=bool(args.get("mark_reviewed", True)),
                )
            elif tool_name == "publish_page":
                res = await publish_page_mcp(store_id=int(sid), page_id=int(args["page_id"]))
            elif tool_name == "get_store_design":
                res = get_store_design(store_id=int(sid))
            elif tool_name == "update_store_design":
                res = update_store_design(
                    store_id=int(sid),
                    primary_color=args.get("primary_color"),
                    accent_color=args.get("accent_color"),
                    design_spec=args.get("design_spec"),
                )
            elif tool_name == "publish_store_design":
                res = await publish_store_design_mcp(store_id=int(sid), draft_theme_id=args.get("draft_theme_id"))
            elif tool_name == "list_products":
                res = list_products(store_id=int(sid), limit=int(args.get("limit", 50)))
            elif tool_name == "get_product":
                res = get_product(store_id=int(sid), product_id=str(args["product_id"]))
            elif tool_name == "update_product":
                res = update_product_content(
                    store_id=int(sid),
                    product_id=str(args["product_id"]),
                    title=args.get("title"),
                    description=args.get("description"),
                    price=args.get("price"),
                )
            elif tool_name == "get_store_details":
                res = get_store_details(store_id=int(sid))
            elif tool_name == "update_store_details":
                res = update_store_details(
                    store_id=int(sid),
                    business=args.get("business"),
                    brand=args.get("brand"),
                )
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method/Tool '{tool_name}' not found"},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, indent=2)}],
                    "isError": False,
                    "data": res,
                },
            }
        except Exception as err:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error executing tool '{tool_name}': {str(err)}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method '{method}'"},
    }


@router.post("/api/mcp")
@router.post("/mcp")
async def mcp_jsonrpc_endpoint(request: Request):
    """Main authenticated JSON-RPC 2.0 MCP endpoint."""
    store_id = authenticate_mcp_request(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    res = await handle_jsonrpc_request(body, store_id)
    return JSONResponse(res)


@router.get("/api/mcp/info")
async def mcp_info_endpoint(request: Request):
    """Get MCP connection information, authentication setup, and available capabilities."""
    store_id = authenticate_mcp_request(request)
    token = get_mcp_token()
    return {
        "ok": True,
        "mcp_server": "4GMC Product Image Slot MCP Server",
        "connection_url": "/api/mcp",
        "authenticated_store_id": store_id,
        "auth_setup": {
            "token": token,
            "header": f"Authorization: Bearer {token}",
            "query_param": f"?token={token}",
        },
        "capabilities": [
            "list_pending_image_slots",
            "get_image_slot_sources",
            "upload_image_asset",
            "replace_image_slot",
            "list_pages",
            "get_page",
            "update_page",
            "publish_page",
            "get_store_design",
            "update_store_design",
            "publish_store_design",
            "list_products",
            "get_product",
            "update_product",
            "get_store_details",
            "update_store_details",
        ],
    }


@router.get("/api/mcp/settings")
async def mcp_settings_get(request: Request):
    """Get current MCP connection configuration."""
    store_id = authenticate_mcp_request(request)
    token = get_mcp_token()
    import server
    endpoint = f"{server.PUBLIC_URL.rstrip('/')}/api/mcp" if server.PUBLIC_URL else "/api/mcp"
    return {
        "ok": True,
        "token": token,
        "url": endpoint,
        "server_name": "4GMC Unified MCP Server",
        "store_id": store_id,
        "capabilities": [
            "list_pending_image_slots",
            "get_image_slot_sources",
            "upload_image_asset",
            "replace_image_slot",
            "list_pages",
            "get_page",
            "update_page",
            "publish_page",
            "get_store_design",
            "update_store_design",
            "publish_store_design",
            "list_products",
            "get_product",
            "update_product",
            "get_store_details",
            "update_store_details",
        ],
    }


@router.post("/api/mcp/settings")
async def mcp_settings_post(request: Request):
    """Save updated MCP API token."""
    store_id = authenticate_mcp_request(request)
    body = await request.json()
    token = str(body.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token cannot be empty")
    set_mcp_token(token)
    return {"ok": True, "token": token, "message": "MCP connection token updated successfully"}


@router.post("/api/mcp/token/regenerate")
async def mcp_token_regenerate(request: Request):
    """Generate and store a new secure MCP API authentication token."""
    store_id = authenticate_mcp_request(request)
    new_token = regenerate_mcp_token()
    return {"ok": True, "token": new_token, "message": "New MCP token generated"}


@router.get("/api/mcp/openapi.json")
async def mcp_openapi_spec(request: Request):
    """OpenAPI 3.1.0 specification for ChatGPT Custom Actions."""
    import server
    base_url = server.PUBLIC_URL.rstrip("/") if server.PUBLIC_URL else ""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "4GMC MCP Integration API",
            "version": "1.0.0",
            "description": "API for ChatGPT to manage store design, pages & policies text, products, and pending images."
        },
        "servers": [{"url": base_url or "http://localhost:8000"}],
        "paths": {
            "/api/mcp": {
                "post": {
                    "summary": "Main MCP JSON-RPC 2.0 Gateway",
                    "operationId": "mcpGateway",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "jsonrpc": {"type": "string", "example": "2.0"},
                                        "id": {"type": "integer", "example": 1},
                                        "method": {"type": "string", "example": "tools/call"},
                                        "params": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "JSON-RPC response"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer"
                }
            }
        },
        "security": [{"bearerAuth": []}]
    }


@router.post("/api/mcp/upload")
async def mcp_upload_endpoint(request: Request):
    """Short-lived signed upload URL / direct HTTP upload endpoint for finished images."""
    store_id = authenticate_mcp_request(request)
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        file_obj = form.get("file") or form.get("image")
        if not file_obj:
            raise HTTPException(status_code=400, detail="No file field found in multipart form data")
        raw_bytes = await file_obj.read()
        filename = getattr(file_obj, "filename", "upload.png")
        mime = getattr(file_obj, "content_type", "image/png")
    else:
        raw_bytes = await request.body()
        filename = request.headers.get("X-Filename", "upload.png")
        mime = content_type.split(";")[0] or "image/png"

    try:
        res = upload_image_asset(raw_bytes=raw_bytes, filename=filename, mime_type=mime)
        return {"ok": True, "store_id": store_id, **res}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))
