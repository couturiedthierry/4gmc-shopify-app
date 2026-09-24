import asyncio
import base64
import json
import sys
from pathlib import Path
from PIL import Image
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gmc_engine
import image_pipeline

async def run_pending_preview_verification():
    print("=== VERIFYING PENDING PREVIEW IMAGE PIPELINE (ZERO API CALLS) ===")
    
    # Check static asset bundled with app
    preview_path = Path("static/preview.png")
    assert preview_path.is_file(), "static/preview.png missing"
    print(f"Verified static preview asset exists: static/preview.png ({preview_path.stat().st_size} bytes)")
    
    # Mock HTTP transport that raises error if any Generative AI endpoint is touched
    def mock_respond(request):
        if "generativelanguage.googleapis.com" in str(request.url):
            raise RuntimeError("VIOLATION: Generative AI image generation API was called!")
        if "cdn.example.com" in str(request.url):
            img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
            import io
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return httpx.Response(200, content=buf.getvalue(), headers={"content-type": "image/png"})
        return httpx.Response(200, json={})

    with image_pipeline.patch_getaddrinfo() if hasattr(image_pipeline, "patch_getaddrinfo") else unittest_dummy():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_respond)) as client:
            results = await image_pipeline.generate_and_attach_images(
                gemini_key="test-key",
                shopify_domain="test.myshopify.com",
                shopify_token="test-token",
                product_gid="gid://shopify/Product/999",
                source_image_urls=["https://cdn.example.com/source-photo-1.png", "https://cdn.example.com/source-photo-2.png"],
                product_title="Commercial Power Washer",
                source_title="High Pressure Washer Unit",
                store_name="VYROX Industrial",
                primary_color="#2251dc",
                accent_color="#6f9cff",
                client=client,
                publish=False,
            )

    print(f"Generated pending image records count: {len(results)}")
    for record in results:
        print("\n--- PENDING RECORD ---")
        print("Product ID:", record["product_id"])
        print("Slot ID / Role:", record["slot_id"])
        print("Source URL:", record["source_url"])
        print("Brand Name:", record["brand_name"])
        print("Logo Reference:", record["logo_ref"])
        print("Status:", record["status"])
        print("Src Asset:", record["src"])
        print("Intended Edit Description:\n" + record["edit_description"])
        
        # Assertions
        assert record["product_id"] == "999"
        assert record["slot_id"] in ("hero", "detail", "lifestyle")
        assert record["status"] == "awaiting_image"
        assert record["src"] == "/static/preview.png"
        assert "Intended Edit Instructions" in record["edit_description"]
        assert "VYROX Industrial" in record["brand_name"]

    print("\nALL ZERO-API PENDING PREVIEW PIPELINE VERIFICATIONS PASSED 100%!")


class unittest_dummy:
    def __enter__(self): pass
    def __exit__(self, *args): pass


if __name__ == "__main__":
    asyncio.run(run_pending_preview_verification())
