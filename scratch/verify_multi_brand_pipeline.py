import asyncio
import base64
import json
import sys
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gmc_engine
import image_pipeline


async def run_multi_brand_verification():
    print("=== MULTI-BRAND & MULTI-CATEGORY PIPELINE VERIFICATION ===")

    # 1. Prepare sample source images for 2 distinct product categories
    # Source A: Lawn Mower (Red box on white)
    img_a = Image.new("RGBA", (512, 512), (255, 255, 255, 255))
    for x in range(100, 412):
        for y in range(150, 450):
            img_a.putpixel((x, y), (30, 180, 50, 255))
    buf_a = BytesIO()
    img_a.save(buf_a, format="PNG")
    bytes_a = buf_a.getvalue()

    # Source B: Pressure Washer / Power Tool (Green box on light gray)
    img_b = Image.new("RGBA", (512, 512), (240, 240, 240, 255))
    for x in range(120, 390):
        for y in range(100, 420):
            img_b.putpixel((x, y), (20, 80, 210, 255))
    buf_b = BytesIO()
    img_b.save(buf_b, format="PNG")
    bytes_b = buf_b.getvalue()

    # 2. Prepare 2 distinct brand kits
    # Brand Kit 1: VYROX Industrial (Blue #2251dc)
    logo_1_img = Image.new("RGBA", (120, 35), (34, 81, 220, 255))
    buf_l1 = BytesIO()
    logo_1_img.save(buf_l1, format="PNG")
    logo_1_bytes = buf_l1.getvalue()

    # Brand Kit 2: AERO Machinery (Crimson #9b1c58)
    logo_2_img = Image.new("RGBA", (120, 35), (155, 28, 88, 255))
    buf_l2 = BytesIO()
    logo_2_img.save(buf_l2, format="PNG")
    logo_2_bytes = buf_l2.getvalue()

    # Mock HTTP transport for testing Gemini API requests
    prompts_captured = []

    def mock_respond(request):
        if request.method == "GET":
            if "mower" in str(request.url):
                return httpx.Response(200, content=bytes_a, headers={"content-type": "image/png"})
            return httpx.Response(200, content=bytes_b, headers={"content-type": "image/png"})
        if request.url.host == "generativelanguage.googleapis.com":
            body = json.loads(request.content)
            prompt_text = body["contents"][0]["parts"][0]["text"]
            prompts_captured.append(prompt_text)
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [
                {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(bytes_a).decode()}}
            ]}}]})
        raise ValueError(f"Unexpected request URL: {request.url}")

    with patch_getaddrinfo():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_respond)) as client:
            # TEST BRAND KIT 1 (VYROX Industrial, #2251dc) on Category A (Walk-Behind Mower)
            res_1 = await image_pipeline.generate_and_attach_images(
                gemini_key="test-key-1",
                shopify_domain="merchant.myshopify.com",
                shopify_token="test-token",
                product_gid="gid://shopify/Product/101",
                source_image_urls=["https://cdn.example.com/mower-front.png"],
                product_title="Walk-Behind Commercial Mower",
                source_title="Commercial Rough Cut Mower",
                store_name="VYROX Industrial",
                primary_color="#2251dc",
                accent_color="#6f9cff",
                logo_mime="image/png",
                logo_bytes=logo_1_bytes,
                roles=("hero",),
                client=client,
                publish=False,
            )

            # TEST BRAND KIT 2 (AERO Machinery, #9b1c58) on Category B (Pressure Washer)
            res_2 = await image_pipeline.generate_and_attach_images(
                gemini_key="test-key-2",
                shopify_domain="merchant.myshopify.com",
                shopify_token="test-token",
                product_gid="gid://shopify/Product/102",
                source_image_urls=["https://cdn.example.com/washer-side.png"],
                product_title="Heavy-Duty Pressure Washer 3500 PSI",
                source_title="Gasoline Pressure Washer Unit",
                store_name="AERO Machinery",
                primary_color="#9b1c58",
                accent_color="#ffc3da",
                logo_mime="image/png",
                logo_bytes=logo_2_bytes,
                roles=("hero",),
                client=client,
                publish=False,
            )

    print("\n--- RESULTS FOR BRAND KIT 1 (VYROX Industrial, #2251dc) ---")
    print(f"Staged assets count: {len(res_1)}")
    print(f"Role: {res_1[0]['role']}")
    print(f"Review decision: {res_1[0]['structured_review']['decision']}")
    print(f"Unmeasured review reason: {res_1[0]['structured_review']['reasons']}")

    print("\n--- RESULTS FOR BRAND KIT 2 (AERO Machinery, #9b1c58) ---")
    print(f"Staged assets count: {len(res_2)}")
    print(f"Role: {res_2[0]['role']}")
    print(f"Review decision: {res_2[0]['structured_review']['decision']}")
    print(f"Unmeasured review reason: {res_2[0]['structured_review']['reasons']}")

    print("\n--- CAPTURED GENERATION PROMPTS ---")
    print(f"Prompt 1 (Brand Kit 1):\n{prompts_captured[0]}\n")
    print(f"Prompt 2 (Brand Kit 2):\n{prompts_captured[1]}\n")

    # Assert dynamic behavior (neither brand nor color is hardcoded)
    assert "#2251dc" in prompts_captured[0]
    assert "VYROX Industrial" in prompts_captured[0]
    assert "#9b1c58" in prompts_captured[1]
    assert "AERO Machinery" in prompts_captured[1]
    assert "VYROX Industrial" not in prompts_captured[1]

    # Assert decision remains needs_review for unmeasured attributes (no automatic approval)
    assert res_1[0]["structured_review"]["decision"] == "needs_review"
    assert res_2[0]["structured_review"]["decision"] == "needs_review"

    print("ALL MULTI-BRAND & MULTI-CATEGORY VERIFICATION CHECKS PASSED 100%!")


def patch_getaddrinfo():
    from unittest.mock import patch
    return patch.object(image_pipeline.socket, "getaddrinfo", return_value=[(0, 0, 0, "", ("1.1.1.1", 443))])


if __name__ == "__main__":
    asyncio.run(run_multi_brand_verification())
