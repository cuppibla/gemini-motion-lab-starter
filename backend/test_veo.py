import asyncio
import os
from google.cloud import storage
import sys

# Add app to path if not running from a module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services import veo_service

async def main():
    print("Finding a test avatar image...")
    client = storage.Client()
    bucket = client.bucket("gemini-motion-lab")
    blobs = bucket.list_blobs()
    
    test_image_uri = None
    for blob in blobs:
        if blob.name.endswith(".png"):
            test_image_uri = f"gs://gemini-motion-lab/{blob.name}"
            break
            
    if not test_image_uri:
        print("No .png found in bucket gs://gemini-motion-lab!")
        return
        
    print(f"Using image: {test_image_uri}")
    
    # Mock motion analysis
    motion_analysis = {
        "summary": "The person is waving happily.",
        "detailed_movements": ["raising right arm", "waving hand side to side"],
        "technical_parameters": {"speed": "normal", "range_of_motion": "high"}
    }
    
    avatar_style = "realistic 3D render, high quality, studio lighting"
    video_id = "test_video_12345"
    
    print("Kicking off Veo video generation...")
    try:
        operation_id = await veo_service.generate_video(
            avatar_image_gcs_uri=test_image_uri,
            motion_analysis=motion_analysis,
            avatar_style=avatar_style,
            location_theme="beach-sunset",
            video_id=video_id
        )
        print(f"Operation started with ID: {operation_id}")
    except Exception as e:
        print(f"Error starting video generation: {e}")
        return
        
    print("Polling...")
    for _ in range(60): # wait up to ~10 mins
        status = await veo_service.poll_operation(operation_id)
        print(f"Status: {status['status']} - {status.get('error', '')}")
        if status["status"] in ("complete", "failed"):
            print(f"Final GCS URI: {status.get('gcs_uri')}")
            break
        await asyncio.sleep(10)
        
    print("Done testing Veo service.")

if __name__ == "__main__":
    asyncio.run(main())
