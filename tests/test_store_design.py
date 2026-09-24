import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
import site_kit


async def test_reference_inspection():
    async def mock_get(url, headers=None):
        class MockResponse:
            status_code = 200
            headers = {"content-type": "text/html"}
            text = "<html><body><div class='hero-banner'>Hero</div><div class='featured-collection'>Collections</div><div class='product-grid'>Products</div><div class='newsletter-box'>Subscribe</div></body></html>"
        return MockResponse()

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        inspection = await site_kit.inspect_reference_design("https://source.example")

    assert inspection["reference_url"] == "https://source.example"
    assert len(inspection["sections"]) >= 2
    assert len(inspection["footer_columns"]) == 4


async def test_store_design_workflow():
    with tempfile.TemporaryDirectory() as temp:
        old_db = server.DB
        server.DB = Path(temp) / "test.db"
        try:
            server.init()
            with server.db() as c:
                c.execute(
                    "UPDATE stores SET domain=?,business=?,brand=? WHERE id=1",
                    (
                        "merchant-test.myshopify.com",
                        json.dumps({
                            "business_name": "VYROX Tools",
                            "domain_name": "vyrox-tools.com",
                            "email": "support@vyrox-tools.com",
                            "phone": "+1 212 555 0199",
                            "address": "456 Tech Park, Austin, TX",
                            "country": "United States",
                            "currency": "USD",
                        }),
                        json.dumps({"color": "#1941ba", "accent": "#6f9cff"}),
                    ),
                )
            client = TestClient(server.app)
            assert client.post("/api/login", json={"password": server.ADMIN_PASSWORD}).status_code == 200

            async def mock_inspect(url):
                return {
                    "sections": [
                        {"type": "hero", "title": "Main Hero Banner", "cta_count": 1},
                        {"type": "featured_collection", "title": "Featured Collections", "grid": 4},
                        {"type": "product_grid", "title": "Curated Products", "grid": 4},
                        {"type": "newsletter", "title": "Newsletter Subscription"},
                    ],
                    "footer_columns": [
                        {"id": "policies", "title": "Our Policies"},
                        {"id": "collections", "title": "Featured Collections"},
                        {"id": "quick_links", "title": "Quick Links"},
                        {"id": "store_info", "title": "Store Information"},
                    ],
                    "reference_url": url,
                }

            with patch.object(site_kit, "source_origin", return_value="https://source.example"), \
                 patch.object(site_kit, "inspect_reference_design", mock_inspect):
                response = client.post("/api/store-design/build", json={"reference_url": "https://source.example"})
            assert response.status_code == 202, response.text
            job = response.json()
            assert job["kind"] == "store_design"

            # Allow job to complete
            await asyncio.sleep(0.8)

            plan_res = client.get("/api/store-design/plan")
            assert plan_res.status_code == 200
            plan = plan_res.json()
            assert plan["brand_name"] == "VYROX Tools"
            assert "enabled_payment_types" in plan["payment_svg_code"]
            assert len(plan["footer_columns"]) == 4
            assert plan["track123_status"] == "verified"
            assert plan["checkout_branding"] == "applied"

            pub_res = client.post("/api/store-design/publish", json={"draft_theme_id": plan["draft_theme_id"]})
            assert pub_res.status_code == 200
            assert pub_res.json()["ok"] is True
            assert pub_res.json()["status"] == "published"
        finally:
            server.DB = old_db


if __name__ == "__main__":
    asyncio.run(test_reference_inspection())
    asyncio.run(test_store_design_workflow())
    print("Store design unit and integration tests passed successfully.")
