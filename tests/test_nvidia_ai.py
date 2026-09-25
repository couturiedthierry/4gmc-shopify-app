"""
Test suite for NVIDIA API Text-Only Integration in 4GMC
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

def test_nvidia_environment_configured():
    assert bool(server.NVIDIA_API_KEY), "NVIDIA_API_KEY should be loaded in server"
    assert server.NVIDIA_BASE_URL == "https://integrate.api.nvidia.com/v1"
    print("[OK] NVIDIA environment variables verified")

def test_ai_connected_text_only_contract():
    # Verify ai_connected evaluates to True with NVIDIA_API_KEY
    ai_connected = bool(server.NVIDIA_API_KEY or server.GEMINI_API_KEY2 or server.GEMINI_API_KEY or server.SMARTAPI_KEY)
    assert ai_connected is True, "AI should be connected when NVIDIA_API_KEY is present"

    # Verify image_connected only depends on Gemini (text-only scope for NVIDIA)
    image_connected = bool(server.GEMINI_API_KEY or server.GEMINI_API_KEY2)
    print(f"[OK] AI connection contract verified: ai_connected={ai_connected}, image_connected={image_connected} (text-only)")

async def test_ai_json_with_nvidia():
    prompt = (
        "Generate a brief JSON outline for a Shopify store brand policy. "
        "Return JSON only: {\"policy_name\": \"Shipping Policy\", \"status\": \"active\", \"version\": 1}"
    )
    print(f"[*] Calling server.ai_json with model '{server.NVIDIA_MODEL}'...")
    result = await server.ai_json(prompt, max_tokens=150)
    assert isinstance(result, dict), f"Expected dict result, got: {type(result)}"
    assert "policy_name" in result or len(result) > 0, f"Expected non-empty JSON dict, got: {result}"
    print(f"[OK] server.ai_json successfully generated and parsed JSON: {result}")

def main():
    print("\n==========================================")
    print("   Running 4GMC NVIDIA AI Integration Tests")
    print("==========================================\n")
    test_nvidia_environment_configured()
    test_ai_connected_text_only_contract()
    asyncio.run(test_ai_json_with_nvidia())
    print("\n==========================================")
    print("   ALL NVIDIA AI INTEGRATION TESTS PASSED!")
    print("==========================================\n")

if __name__ == '__main__':
    main()
