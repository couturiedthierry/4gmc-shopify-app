import base64
import io
import json
import sys
import tempfile
import time
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import mcp_server

def test_mcp_image_slots_pipeline():
    with tempfile.TemporaryDirectory() as temp:
        server.DB = Path(temp) / "test_mcp.db"
        server.init()

        # 1. Setup mock store and product in DB
        with server.db() as c:
            c.execute(
                "UPDATE stores SET name=?, domain=?, brand=?, business=? WHERE id=1",
                (
                    "VYROX Industrial",
                    "vyrox-test.myshopify.com",
                    json.dumps({"color": "#2251dc", "accent": "#6f9cff", "logo": {"extension": "png", "content_type": "image/png"}}),
                    json.dumps({"business_name": "VYROX Industrial", "currency": "USD"}),
                ),
            )
            prod_id = c.execute(
                "INSERT INTO products(store_id, source_url, source_title, title, description, price, sku, gtin, images, source_data) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    1,
                    "https://supplier.example.com/photos/lawnmower-original.jpg",
                    "Commercial Lawnmower Unit",
                    "VYROX Pro Lawnmower",
                    "Heavy duty commercial lawnmower.",
                    "499.00",
                    "LM-100",
                    "",
                    json.dumps([
                        "https://supplier.example.com/photos/lawnmower-original.jpg",
                        "https://supplier.example.com/photos/lawnmower-detail.jpg"
                    ]),
                    json.dumps({"category": "lawnmowers"}),
                ),
            ).lastrowid

        client = TestClient(server.app)
        mcp_token = mcp_server.get_mcp_token()
        assert mcp_token, "MCP API Token must be initialized"

        # -------------------------------------------------------------
        # TEST 1: Unauthenticated request fails with 401
        # -------------------------------------------------------------
        unauth_resp = client.post("/api/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert unauth_resp.status_code == 401, f"Expected 401, got {unauth_resp.status_code}"
        assert "Unauthorized" in unauth_resp.json()["detail"]

        # -------------------------------------------------------------
        # TEST 2: MCP Connection Info Endpoint
        # -------------------------------------------------------------
        info_resp = client.get(f"/api/mcp/info?token={mcp_token}")
        assert info_resp.status_code == 200
        info_data = info_resp.json()
        assert info_data["ok"] is True
        assert info_data["mcp_server"] == "4GMC Product Image Slot MCP Server"
        assert "list_pending_image_slots" in info_data["capabilities"]

        headers = {"Authorization": f"Bearer {mcp_token}"}

        # -------------------------------------------------------------
        # TEST 3: JSON-RPC initialize & tools/list
        # -------------------------------------------------------------
        init_resp = client.post("/api/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        assert init_resp.status_code == 200
        assert init_resp.json()["result"]["serverInfo"]["name"] == "4GMC Product Image Slot MCP Server"

        list_tools_resp = client.post("/api/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert list_tools_resp.status_code == 200
        tool_names = [t["name"] for t in list_tools_resp.json()["result"]["tools"]]
        assert "list_pending_image_slots" in tool_names
        assert "get_image_slot_sources" in tool_names
        assert "upload_image_asset" in tool_names
        assert "replace_image_slot" in tool_names

        # -------------------------------------------------------------
        # TEST 4: list_pending_image_slots returns initial awaiting_image slots
        # -------------------------------------------------------------
        slots_resp = client.post(
            "/api/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "list_pending_image_slots",
                    "arguments": {"product_id": str(prod_id)},
                },
            },
        )
        assert slots_resp.status_code == 200
        res_json = slots_resp.json()
        assert "result" in res_json and "data" in res_json["result"], f"Error in list_pending_image_slots: {res_json}"
        result_data = res_json["result"]["data"]
        assert len(result_data) == 3, f"Expected 3 image slots (hero, detail, lifestyle), got {len(result_data)}"

        slots_by_role = {slot["slot_id"]: slot for slot in result_data}
        assert "hero" in slots_by_role
        assert "detail" in slots_by_role
        assert "lifestyle" in slots_by_role

        for role in ("hero", "detail", "lifestyle"):
            slot = slots_by_role[role]
            assert slot["product_id"] == str(prod_id)
            assert slot["status"] == "awaiting_image"
            assert slot["src"] == "/static/preview.png"
            assert slot["dimensions"] == {"width": 2048, "height": 2048, "aspect_ratio": "1:1"}
            assert "Intended Edit Instructions" in slot["intended_edit_description"]

        # -------------------------------------------------------------
        # TEST 5: get_image_slot_sources returns source photography & brand instructions
        # -------------------------------------------------------------
        sources_resp = client.post(
            "/api/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "get_image_slot_sources",
                    "arguments": {"product_id": str(prod_id), "slot_id": "hero"},
                },
            },
        )
        assert sources_resp.status_code == 200
        sources_data = sources_resp.json()["result"]["data"]
        assert sources_data["product_id"] == str(prod_id)
        assert sources_data["slot_id"] == "hero"
        assert sources_data["original_source_image_url"] == "https://supplier.example.com/photos/lawnmower-original.jpg"
        assert sources_data["brand_identity"]["brand_name"] == "VYROX Industrial"
        assert sources_data["brand_identity"]["primary_color"] == "#2251dc"
        assert "signed_upload_url" in sources_data["upload_mechanism"]

        # -------------------------------------------------------------
        # TEST 6: upload_image_asset accepts finished image base64 & returns asset_id
        # -------------------------------------------------------------
        # Create a test synthetic finished image in memory
        test_img = Image.new("RGBA", (400, 400), (34, 81, 220, 255))
        buf = io.BytesIO()
        test_img.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        b64_str = base64.b64encode(img_bytes).decode()

        upload_resp = client.post(
            "/api/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "upload_image_asset",
                    "arguments": {"image_data": f"data:image/png;base64,{b64_str}", "filename": "finished_hero.png"},
                },
            },
        )
        assert upload_resp.status_code == 200
        upload_data = upload_resp.json()["result"]["data"]
        asset_id = upload_data["asset_id"]
        assert asset_id.startswith("asset_"), f"Invalid asset_id {asset_id}"
        asset_url = upload_data["url"]
        assert asset_url.startswith("/static/uploads/"), f"Invalid asset URL {asset_url}"

        # -------------------------------------------------------------
        # TEST 7: replace_image_slot updates ONLY the intended slot (hero)
        # -------------------------------------------------------------
        replace_resp = client.post(
            "/api/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "replace_image_slot",
                    "arguments": {
                        "product_id": str(prod_id),
                        "slot_id": "hero",
                        "asset_id": asset_id,
                    },
                },
            },
        )
        assert replace_resp.status_code == 200
        replace_json = replace_resp.json()
        assert "result" in replace_json and "data" in replace_json["result"], f"Error in replace_image_slot: {replace_json}"
        replace_data = replace_json["result"]["data"]
        assert replace_data["ok"] is True
        assert replace_data["slot_id"] == "hero"
        assert replace_data["status"] == "ready_for_review"
        assert replace_data["src"] == asset_url
        assert replace_data["shopify_published"] is False

        # Verify database state for all slots on product #prod_id
        with server.db() as c:
            prod_row = c.execute("SELECT * FROM products WHERE id=?", (prod_id,)).fetchone()
            manifest_after = json.loads(prod_row["ai_image_manifest"])
            slots_after = {item["slot_id"]: item for item in manifest_after}

            # Hero slot MUST be updated to ready_for_review with asset_url
            assert slots_after["hero"]["status"] == "ready_for_review"
            assert slots_after["hero"]["src"] == asset_url
            assert slots_after["hero"]["asset_id"] == asset_id
            assert slots_after["hero"]["source_url"] == "https://supplier.example.com/photos/lawnmower-original.jpg"

            # Detail and Lifestyle slots MUST remain untouched as awaiting_image with preview.png!
            assert slots_after["detail"]["status"] == "awaiting_image"
            assert slots_after["detail"]["src"] == "/static/preview.png"
            assert slots_after["lifestyle"]["status"] == "awaiting_image"
            assert slots_after["lifestyle"]["src"] == "/static/preview.png"

        # -------------------------------------------------------------
        # TEST 8: Test signed HTTP POST upload URL endpoint
        # -------------------------------------------------------------
        signed_token = mcp_server.generate_signed_upload_token(store_id=1)
        http_upload_resp = client.post(
            f"/api/mcp/upload?signed_token={signed_token}",
            content=img_bytes,
            headers={"Content-Type": "image/png", "X-Filename": "detail_finished.png"},
        )
        assert http_upload_resp.status_code == 200
        http_upload_data = http_upload_resp.json()
        assert http_upload_data["ok"] is True
        detail_asset_id = http_upload_data["asset_id"]

        # Replace detail slot via detail_asset_id
        client.post(
            "/api/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "replace_image_slot",
                    "arguments": {
                        "product_id": str(prod_id),
                        "slot_id": "detail",
                        "asset_id": detail_asset_id,
                    },
                },
            },
        )

        with server.db() as c:
            prod_row = c.execute("SELECT * FROM products WHERE id=?", (prod_id,)).fetchone()
            manifest_after2 = json.loads(prod_row["ai_image_manifest"])
            slots_after2 = {item["slot_id"]: item for item in manifest_after2}

            assert slots_after2["hero"]["status"] == "ready_for_review"
            assert slots_after2["detail"]["status"] == "ready_for_review"
            assert slots_after2["detail"]["asset_id"] == detail_asset_id
            # Lifestyle slot remains awaiting_image
            assert slots_after2["lifestyle"]["status"] == "awaiting_image"
            assert slots_after2["lifestyle"]["src"] == "/static/preview.png"

        print("\nALL MCP IMAGE SLOT INTEGRATION TESTS PASSED 100%!")


if __name__ == "__main__":
    test_mcp_image_slots_pipeline()
