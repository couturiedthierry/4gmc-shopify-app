import sys
import traceback

try:
    import server
    print("server.py imported successfully!")
except ModuleNotFoundError as e:
    print("ModuleNotFoundError occurred during import:")
    traceback.print_exc()
except Exception as e:
    print(f"Other error occurred: {e}")
    traceback.print_exc()

# Let's also try to simulate the job
import asyncio

async def test_job():
    try:
        from server import generate_site_kit
        # Mock data
        class MockData:
            source_url = ""
        
        await generate_site_kit(MockData())
        print("generate_site_kit ran successfully!")
    except Exception as e:
        print("Error during generate_site_kit:")
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_job())
