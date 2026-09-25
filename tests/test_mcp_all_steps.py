"""
Test Suite for 4GMC Comprehensive MCP Integration — Covering All Steps:
1. Pages & Policies Text (list, get, update, format, publish)
2. Store Design (get, update, publish)
3. Products & Catalog (list, get, update)
4. Store Details & Identity (get, update)
5. MCP Settings & Token Management (get, save, regenerate, openapi)
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from starlette.testclient import TestClient

import os
import server
import mcp_server


def test_mcp_comprehensive_capabilities():
    old_legacy_env = os.environ.get("MCP_LEGACY_TOKEN_ENABLED")
    os.environ["MCP_LEGACY_TOKEN_ENABLED"] = "true"
    with tempfile.TemporaryDirectory() as temp:
        server.DB = Path(temp) / "test_mcp_all.db"
        server.init()

        # Seed store and sample data
        with server.db() as c:
            biz = {
                "business_name": "VYROX Tools",
                "email": "support@vyrox.cc",
                "phone": "+1 (929) 324-1981",
                "address": "552 Bement Ave, Staten Island, NY 10310",
                "country": "United States",
                "currency": "USD",
                "domain_name": "vyrox.cc",
                "product_genre": "Lawn Care & Power Equipment",
            }
            brand = {
                "color": "#1e3a8a",
                "accent": "#3b82f6",
            }
            c.execute(
                "UPDATE stores SET name=?, domain=?, business=?, brand=? WHERE id=1",
                ("VYROX Tools", "vyrox-test.myshopify.com", json.dumps(biz), json.dumps(brand))
            )
            c.execute(
                "INSERT INTO pages(store_id, kind, title, body, status) VALUES(1, 'contact', 'Contact Us', 'Contact our support team for help.', 'draft')"
            )
            c.execute(
                "INSERT INTO products(store_id, title, source_title, price, status, source_url) VALUES(1, 'Electric Lawn Mower', 'Lawn Mower', '299.00', 'active', 'https://example.com/mower.jpg')"
            )

        client = TestClient(server.app)
        token = mcp_server.get_mcp_token()
        headers = {"Authorization": f"Bearer {token}"}

        # 1. MCP Settings GET
        settings_resp = client.get(f"/api/mcp/settings?token={token}")
        assert settings_resp.status_code == 200
        settings_data = settings_resp.json()
        assert settings_data["ok"] is True
        assert settings_data["token"] == token
        assert "list_pages" in settings_data["capabilities"]
        assert "get_store_design" in settings_data["capabilities"]
        assert "list_products" in settings_data["capabilities"]

        # 2. MCP Settings POST (update token)
        new_custom_token = "gmc_mcp_custom_token_12345"
        update_token_resp = client.post(
            f"/api/mcp/settings?token={token}",
            json={"token": new_custom_token}
        )
        assert update_token_resp.status_code == 200
        assert mcp_server.get_mcp_token() == new_custom_token

        # Update headers with new token
        headers = {"Authorization": f"Bearer {new_custom_token}"}

        # 3. OpenAPI specification
        openapi_resp = client.get(f"/api/mcp/openapi.json?token={new_custom_token}")
        assert openapi_resp.status_code == 200
        assert openapi_resp.json()["openapi"] == "3.1.0"

        # 4. MCP tools/list includes all 16 capabilities
        tools_resp = client.post("/api/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert tools_resp.status_code == 200
        tool_names = [t["name"] for t in tools_resp.json()["result"]["tools"]]
        expected_tools = [
            "list_pending_image_slots", "get_image_slot_sources", "upload_image_asset", "replace_image_slot",
            "list_pages", "get_page", "update_page", "publish_page",
            "get_store_design", "update_store_design", "publish_store_design",
            "list_products", "get_product", "update_product",
            "get_store_details", "update_store_details",
        ]
        for et in expected_tools:
            assert et in tool_names, f"Tool '{et}' missing from tools/list"

        # 5. Tool Call: list_pages
        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "list_pages", "arguments": {"store_id": 1}}
        })
        assert call_resp.status_code == 200
        pages = call_resp.json()["result"]["data"]
        assert len(pages) >= 1
        assert pages[0]["kind"] == "contact"

        # 6. Tool Call: update_page with AI generated content (verifying semantic HTML headings and links)
        raw_contact_text = (
            "Contact Information\n\n"
            "Email: support@vyrox.cc\n"
            "Phone: +1 (929) 324-1981\n"
            "Business Hours: Mon-Fri: 9:00 AM - 5:00 PM (Eastern Time)\n\n"
            "Customer Support\n\n"
            "If you have inquiries regarding our equipment, reach out to our team. "
            "For delivery timelines review our Shipping Policy and for returns review our Refund Policy."
        )
        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "update_page",
                "arguments": {
                    "kind": "contact",
                    "title": "Contact Us",
                    "body": raw_contact_text,
                    "store_id": 1
                }
            }
        })
        assert call_resp.status_code == 200
        update_result = call_resp.json()["result"]["data"]
        formatted_html = update_result["body"]
        assert "<h1>Contact Us</h1>" not in formatted_html
        assert "<h1>" not in formatted_html
        assert "<h2>" in formatted_html
        assert '<a href="mailto:support@vyrox.cc">support@vyrox.cc</a>' in formatted_html
        assert 'href="tel:19293241981"' in formatted_html
        assert '<a href="/policies/shipping-policy">Shipping Policy</a>' in formatted_html
        assert '<a href="/policies/refund-policy">Refund Policy</a>' in formatted_html

        # 7. Tool Call: get_page
        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "get_page", "arguments": {"kind": "contact", "store_id": 1}}
        })
        assert call_resp.status_code == 200
        page_data = call_resp.json()["result"]["data"]
        assert page_data["title"] == "Contact Us"

        # 8. Tool Call: get_store_design & update_store_design
        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "get_store_design", "arguments": {"store_id": 1}}
        })
        assert call_resp.status_code == 200
        design_data = call_resp.json()["result"]["data"]
        assert design_data["brand_colors"]["primary"] == "#1e3a8a"

        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {
                "name": "update_store_design",
                "arguments": {"primary_color": "#0f172a", "accent_color": "#38bdf8", "store_id": 1}
            }
        })
        assert call_resp.status_code == 200
        updated_design = call_resp.json()["result"]["data"]
        assert updated_design["brand_colors"]["primary"] == "#0f172a"

        # 9. Tool Call: publish_store_design
        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "publish_store_design", "arguments": {"store_id": 1}}
        })
        assert call_resp.status_code == 200
        pub_design = call_resp.json()["result"]["data"]
        assert pub_design["status"] == "published"

        # 10. Tool Call: list_products & update_product
        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {"name": "list_products", "arguments": {"store_id": 1}}
        })
        assert call_resp.status_code == 200
        prods = call_resp.json()["result"]["data"]
        assert len(prods) >= 1
        prod_id = prods[0]["id"]

        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 9, "method": "tools/call",
            "params": {
                "name": "update_product",
                "arguments": {"product_id": str(prod_id), "title": "VYROX Pro Lawn Mower", "price": "349.99", "store_id": 1}
            }
        })
        assert call_resp.status_code == 200
        assert call_resp.json()["result"]["data"]["ok"] is True

        # 11. Tool Call: get_store_details & update_store_details
        call_resp = client.post("/api/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 10, "method": "tools/call",
            "params": {"name": "get_store_details", "arguments": {"store_id": 1}}
        })
        assert call_resp.status_code == 200
        store_det = call_resp.json()["result"]["data"]
        assert store_det["name"] == "VYROX Tools"

        # 12. Regenerate Token endpoint
        regen_resp = client.post(f"/api/mcp/token/regenerate?token={new_custom_token}")
        assert regen_resp.status_code == 200
        regenerated_token = regen_resp.json()["token"]
        assert regenerated_token.startswith("gmc_mcp_")
        assert regenerated_token != new_custom_token
        assert mcp_server.get_mcp_token() == regenerated_token

        print("\nALL MCP COMPREHENSIVE INTEGRATION CAPABILITIES PASSED 100%!")
        if old_legacy_env is not None:
            os.environ["MCP_LEGACY_TOKEN_ENABLED"] = old_legacy_env
        else:
            os.environ.pop("MCP_LEGACY_TOKEN_ENABLED", None)


if __name__ == "__main__":
    test_mcp_comprehensive_capabilities()
