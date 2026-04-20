import os
import sys
import json
from google.cloud import storage

# Add app to path if not running from a module
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services import gemini_service

def upload_local_to_gcs(local_path: str, bucket_name: str, dest_blob_name: str) -> str:
    print(f"Uploading {local_path} to gs://{bucket_name}/{dest_blob_name}...")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{dest_blob_name}"

def main():
    print("Testing Gemini generate_content...")
    
    local_video = os.path.abspath(os.path.join(os.path.dirname(__file__), "../test_video.mp4"))
    if not os.path.exists(local_video):
        print(f"File not found: {local_video}")
        return
        
    bucket = "gemini-motion-lab"
    blob_name = "test/manga-1.mp4"
    
    try:
        gcs_uri = upload_local_to_gcs(local_video, bucket, blob_name)
        print(f"Uploaded to {gcs_uri}")
    except Exception as e:
        print(f"Failed to upload to GCS: {e}")
        return
    
    try:
        print(f"Calling Gemini analyze_video_sync with url={gcs_uri}")
        result = gemini_service.analyze_video_sync(gcs_uri)
        print("Success! Received reasoning back:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error testing gemini: {e}")

if __name__ == "__main__":
    main()
