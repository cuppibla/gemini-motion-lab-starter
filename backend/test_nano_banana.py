import asyncio
import os
import sys

# Add app to path if not running from a module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services import nano_banana_service

async def main():
    print("Testing Nano Banana generate_avatar_image...")
    
    # Use a mock input image
    frame_bytes = nano_banana_service._MOCK_PNG_BYTES
    style_key = "manga-ink"
    
    try:
        print(f"Calling Nano Banana with style_key={style_key}")
        result_bytes = await nano_banana_service.generate_avatar_image(
            frame_bytes=frame_bytes, style_key=style_key
        )
        print(f"Success! Received {len(result_bytes)} bytes back.")
        
        # Save it to a file
        out_path = "test_nano_output.png"
        with open(out_path, "wb") as f:
            f.write(result_bytes)
        print(f"Saved output to {out_path}")
    except Exception as e:
        print(f"Error testing nano banana: {e}")

if __name__ == "__main__":
    asyncio.run(main())
