#!/usr/bin/env python3
"""One-off: regenerate watercolor-2.mp4 using watercolor-2.png as a reference image."""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from google import genai
from google.cloud import storage
from google.genai import types
from app.prompts.video_generation import build_video_prompt

PROJECT  = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
BUCKET   = os.environ["GCS_BUCKET"]

PNG_PATH    = Path(__file__).parent.parent / "frontend/public/showcase/watercolor-2.png"
OUTPUT_PATH = Path(__file__).parent.parent / "frontend/public/showcase/watercolor-2.mp4"
GCS_KEY     = "showcase-ref/watercolor-2.png"

MOTION_DATA = {
    "veo_prompt": "A young Middle Eastern male character performs a dabke-inspired stepping dance, rhythmic foot stamps with synchronized arm movements",
    "person_description": "young adult male, Middle Eastern features, dark curly hair, athletic build",
    "overall_style": "rhythmic and grounded",
    "camera_angle": "medium shot",
    "phases": [
        {"time_range": "0-1s", "action": "stamp right foot forward and clap hands", "tempo": "medium", "energy": "high"},
        {"time_range": "1-2s", "action": "step side to side with linked arm swing", "tempo": "medium", "energy": "high"},
        {"time_range": "2-3s", "action": "stamp sequence with raised fist celebration", "tempo": "fast", "energy": "very high"},
    ],
}

async def main():
    # 1. Upload PNG to GCS so Veo can use it as a reference image
    print(f"Uploading {PNG_PATH.name} to gs://{BUCKET}/{GCS_KEY} ...")
    gcs_client = storage.Client(project=PROJECT)
    blob = gcs_client.bucket(BUCKET).blob(GCS_KEY)
    blob.upload_from_filename(str(PNG_PATH), content_type="image/png")
    gcs_uri = f"gs://{BUCKET}/{GCS_KEY}"
    print(f"  Uploaded: {gcs_uri}")

    # 2. Build prompt and call Veo with the PNG as a reference image
    prompt = build_video_prompt(MOTION_DATA, "watercolor-dream", "golden-desert")
    print(f"\nPrompt (truncated): {prompt[:120]}...")

    client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)

    print("\nStarting Veo generation (reference image mode)...")
    operation = client.models.generate_videos(
        model="veo-3.1-fast-generate-001",
        prompt=prompt,
        config=types.GenerateVideosConfig(
            reference_images=[
                types.VideoGenerationReferenceImage(
                    image=types.Image(gcs_uri=gcs_uri, mime_type="image/png"),
                    reference_type="ASSET",
                )
            ],
            aspect_ratio="9:16",
            number_of_videos=1,
            duration_seconds=8,
            output_gcs_uri=f"gs://{BUCKET}/showcase-gen/watercolor-2-regen/",
        ),
    )

    # 3. Poll until done
    print("  Polling", end="", flush=True)
    while not operation.done:
        await asyncio.sleep(10)
        operation = client.operations.get(operation)
        print(".", end="", flush=True)
    print()

    if not (operation.result and operation.result.generated_videos):
        print("ERROR: No video in result:", operation)
        sys.exit(1)

    # 4. Download to local file
    video_gcs_uri = operation.result.generated_videos[0].video.uri
    print(f"  Video ready: {video_gcs_uri}")
    path_part = video_gcs_uri.replace(f"gs://{BUCKET}/", "")
    blob = gcs_client.bucket(BUCKET).blob(path_part)
    blob.download_to_filename(str(OUTPUT_PATH))
    print(f"\nSaved: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    asyncio.run(main())
