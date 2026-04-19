#!/usr/bin/env python3
"""
generate_showcase.py
--------------------
Generates 12 curated showcase videos for the kiosk gallery.
Videos are saved to frontend/public/showcase/ as static assets.

Usage:
    cd /path/to/gemini-motion-lab
    pip install google-genai google-cloud-storage python-dotenv
    python scripts/generate_showcase.py

Requirements:
    - GOOGLE_CLOUD_PROJECT set in environment or .env
    - GCS_BUCKET set in environment or .env
    - Valid Vertex AI credentials (gcloud auth application-default login)
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load backend .env
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from google import genai
from google.genai import types
from app.prompts.video_generation import build_video_prompt

PROJECT = os.environ["GOOGLE_CLOUD_PROJECT"]
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
BUCKET = os.environ["GCS_BUCKET"]
OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "public" / "showcase"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------
# 12-video diversity matrix
# Each entry: (filename, avatar_style, location_theme, mock_motion_analysis)
# -----------------------------------------------------------------------
SHOWCASE_MATRIX = [
    ("pixel-hero-1", "pixel-hero", "lunar-surface", {
        "veo_prompt": "A young Black male character performs a joyful Afrobeats-inspired groove, stepping side to side with rhythmic shoulder rolls and expressive arm movements",
        "person_description": "young adult male, dark skin, short natural hair, athletic build",
        "overall_style": "rhythmic and energetic",
        "camera_angle": "medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "step to the right with shoulder roll", "tempo": "medium", "energy": "high"},
            {"time_range": "1-2s", "action": "step to the left with arm swing", "tempo": "medium", "energy": "high"},
            {"time_range": "2-3s", "action": "full body groove with raised hands", "tempo": "medium", "energy": "high"},
        ],
    }),
    ("pixel-hero-2", "pixel-hero", "neon-city", {
        "veo_prompt": "A teenage East Asian female character performs a joyful jump and wave greeting, leaping upward with both arms raised celebrating",
        "person_description": "teenage female, East Asian features, straight black hair, slender build",
        "overall_style": "light and joyful",
        "camera_angle": "medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "crouch in preparation", "tempo": "fast", "energy": "medium"},
            {"time_range": "1-2s", "action": "jump upward with arms raised high", "tempo": "fast", "energy": "high"},
            {"time_range": "2-3s", "action": "land and wave both hands enthusiastically", "tempo": "medium", "energy": "high"},
        ],
    }),
    ("cyber-nova-1", "cyber-nova", "enchanted-forest", {
        "veo_prompt": "A young South Asian female character performs graceful Bollywood-inspired arm movements, flowing figure-eight arm arcs with subtle hip sway",
        "person_description": "young adult female, South Asian features, dark wavy hair, graceful posture",
        "overall_style": "graceful and fluid",
        "camera_angle": "medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "right arm flows upward in arc while left stays low", "tempo": "slow", "energy": "medium"},
            {"time_range": "1-2s", "action": "both arms trace figure-eight with hip sway", "tempo": "slow", "energy": "medium"},
            {"time_range": "2-3s", "action": "arms reach wide in open embrace pose", "tempo": "slow", "energy": "medium"},
        ],
    }),
    ("cyber-nova-2", "cyber-nova", "space-station", {
        "veo_prompt": "A middle-aged White male character strikes a confident heroic power pose, feet planted wide, chest out, arms crossing then spreading wide",
        "person_description": "middle-aged male, light skin, short salt-and-pepper hair, strong build",
        "overall_style": "powerful and confident",
        "camera_angle": "low-angle medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "plant feet wide and stand tall with arms at sides", "tempo": "slow", "energy": "high"},
            {"time_range": "1-2s", "action": "cross arms over chest powerfully", "tempo": "slow", "energy": "high"},
            {"time_range": "2-3s", "action": "spread arms wide in heroic open stance", "tempo": "slow", "energy": "high"},
        ],
    }),
    ("watercolor-1", "watercolor-dream", "underwater-palace", {
        "veo_prompt": "An older Latina female character performs graceful tai chi arm movements, slow flowing circular arm sweeps with weight shifting gently",
        "person_description": "older adult female, Latina features, silver-streaked dark hair, serene expression",
        "overall_style": "slow and meditative",
        "camera_angle": "soft front-facing medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "arms rise slowly in wide arc outward", "tempo": "very slow", "energy": "low"},
            {"time_range": "1-2s", "action": "circular arm sweep drawing energy inward", "tempo": "very slow", "energy": "low"},
            {"time_range": "2-3s", "action": "push outward gently with both palms, weight shifts", "tempo": "very slow", "energy": "low"},
        ],
    }),
    ("watercolor-2", "watercolor-dream", "golden-desert", {
        "veo_prompt": "A young Middle Eastern male character performs a dabke-inspired stepping dance, rhythmic foot stamps with synchronized arm movements",
        "person_description": "young adult male, Middle Eastern features, dark curly hair, athletic build",
        "overall_style": "rhythmic and grounded",
        "camera_angle": "medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "stamp right foot forward and clap hands", "tempo": "medium", "energy": "high"},
            {"time_range": "1-2s", "action": "step side to side with linked arm swing", "tempo": "medium", "energy": "high"},
            {"time_range": "2-3s", "action": "stamp sequence with raised fist celebration", "tempo": "fast", "energy": "very high"},
        ],
    }),
    ("figurine-1", "3d-figurine", "neon-city", {
        "veo_prompt": "A teenage Southeast Asian male character performs smooth K-pop inspired choreography with precise arm isolations and head bob",
        "person_description": "teenage male, Southeast Asian features, styled dark hair, slender build",
        "overall_style": "precise and stylish",
        "camera_angle": "front-facing medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "arm isolation left with head snap", "tempo": "medium", "energy": "medium"},
            {"time_range": "1-2s", "action": "smooth body wave with finger point", "tempo": "medium", "energy": "medium"},
            {"time_range": "2-3s", "action": "sharp pose with crossed arms and confident lean", "tempo": "fast", "energy": "high"},
        ],
    }),
    ("figurine-2", "3d-figurine", "lunar-surface", {
        "veo_prompt": "A middle-aged Black female character performs a soulful slow dance, swaying arms and body with emotional expressiveness",
        "person_description": "middle-aged female, Black features, natural hair, full figure, serene expression",
        "overall_style": "soulful and expressive",
        "camera_angle": "front-facing medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "sway body left with outstretched right arm", "tempo": "slow", "energy": "medium"},
            {"time_range": "1-2s", "action": "gentle spin with arms flowing behind", "tempo": "slow", "energy": "medium"},
            {"time_range": "2-3s", "action": "sway back with hands clasped at heart", "tempo": "slow", "energy": "low"},
        ],
    }),
    ("manga-1", "manga-ink", "space-station", {
        "veo_prompt": "A young East Asian male character performs a dynamic martial arts kata with a sharp punch sequence and powerful kick",
        "person_description": "young adult male, East Asian features, short dark hair, athletic muscular build",
        "overall_style": "explosive and precise",
        "camera_angle": "medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "guard stance with fists raised, sharp ready position", "tempo": "fast", "energy": "high"},
            {"time_range": "1-2s", "action": "explosive front punch sequence left-right-left", "tempo": "very fast", "energy": "very high"},
            {"time_range": "2-3s", "action": "powerful roundhouse kick with arm balance", "tempo": "fast", "energy": "very high"},
        ],
    }),
    ("manga-2", "manga-ink", "golden-desert", {
        "veo_prompt": "An older White female character performs an elegant ballroom dance gesture, graceful arm extension with a slight bow and sweeping arm arc",
        "person_description": "older adult female, light skin, silver hair in elegant updo, poised posture",
        "overall_style": "elegant and refined",
        "camera_angle": "medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "stand tall with one arm extended outward gracefully", "tempo": "slow", "energy": "low"},
            {"time_range": "1-2s", "action": "slight bow with arm sweeping downward", "tempo": "slow", "energy": "low"},
            {"time_range": "2-3s", "action": "rise and arc arm overhead in flowing gesture", "tempo": "slow", "energy": "medium"},
        ],
    }),
    ("brick-1", "brick-build", "enchanted-forest", {
        "veo_prompt": "A young Indigenous female character performs a celebratory clap and spin, joyful full-body rotation with hands clapping overhead",
        "person_description": "young adult female, Indigenous features, long dark braided hair, joyful expression",
        "overall_style": "celebratory and joyful",
        "camera_angle": "front-facing medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "clap hands overhead three times with big smile", "tempo": "fast", "energy": "high"},
            {"time_range": "1-2s", "action": "full 360-degree spin with arms out", "tempo": "fast", "energy": "high"},
            {"time_range": "2-3s", "action": "land facing forward with arms raised in victory", "tempo": "medium", "energy": "very high"},
        ],
    }),
    ("brick-2", "brick-build", "underwater-palace", {
        "veo_prompt": "A teenage Latino male character performs a capoeira-inspired ginga sweep, fluid rocking side-to-side with a low spinning leg sweep",
        "person_description": "teenage male, Latino features, curly dark hair, athletic flexible build",
        "overall_style": "fluid and dynamic",
        "camera_angle": "front-facing medium shot",
        "phases": [
            {"time_range": "0-1s", "action": "ginga rocking side to side with loose arms", "tempo": "medium", "energy": "medium"},
            {"time_range": "1-2s", "action": "low crouching sweep kick from right to left", "tempo": "fast", "energy": "high"},
            {"time_range": "2-3s", "action": "flow back up into ready stance with raised guard", "tempo": "medium", "energy": "high"},
        ],
    }),
]


async def generate_and_download(client, entry: tuple, semaphore: asyncio.Semaphore) -> None:
    filename, avatar_style, location_theme, motion_data = entry
    output_path = OUTPUT_DIR / f"{filename}.mp4"

    if output_path.exists():
        print(f"  ✓ Skipping {filename}.mp4 (already exists)")
        return

    print(f"  → Starting: {filename} ({avatar_style} in {location_theme})")

    async with semaphore:
        try:
            prompt = build_video_prompt(motion_data, avatar_style, location_theme)

            operation = await client.aio.models.generate_videos(
                model="veo-3.1-fast-generate-001",
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    number_of_videos=1,
                    duration_seconds=8,
                    output_gcs_uri=f"gs://{BUCKET}/showcase-gen/{filename}/",
                ),
            )

            # Poll until done
            while not operation.done:
                await asyncio.sleep(10)
                operation = await client.aio.operations.get(operation)

            if operation.result and operation.result.generated_videos:
                gcs_uri = operation.result.generated_videos[0].video.uri
                # Download from GCS
                from google.cloud import storage
                gcs_client = storage.Client(project=PROJECT)
                # Parse gs://bucket/path
                path_part = gcs_uri.replace(f"gs://{BUCKET}/", "")
                blob = gcs_client.bucket(BUCKET).blob(path_part)
                blob.download_to_filename(str(output_path))
                print(f"  ✅ Done: {filename}.mp4 saved ({output_path.stat().st_size // 1024}KB)")
            else:
                print(f"  ❌ Failed: {filename} — no video in result")

        except Exception as e:
            print(f"  ❌ Error generating {filename}: {e}")


async def main():
    print(f"Gemini Motion Lab — Showcase Video Generator")
    print(f"Project: {PROJECT} | Bucket: {BUCKET}")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Generating {len(SHOWCASE_MATRIX)} videos in parallel...\n")

    client = genai.Client(
        vertexai=True,
        project=PROJECT,
        location=LOCATION,
    )

    # Limit concurrent Veo jobs to avoid quota issues
    semaphore = asyncio.Semaphore(6)

    tasks = [
        generate_and_download(client, entry, semaphore)
        for entry in SHOWCASE_MATRIX
    ]
    await asyncio.gather(*tasks)

    # Summary
    generated = list(OUTPUT_DIR.glob("*.mp4"))
    print(f"\n{'='*50}")
    print(f"✅ Done! {len(generated)}/{len(SHOWCASE_MATRIX)} videos in {OUTPUT_DIR}")
    if len(generated) < len(SHOWCASE_MATRIX):
        missing = [e[0] for e in SHOWCASE_MATRIX if not (OUTPUT_DIR / f"{e[0]}.mp4").exists()]
        print(f"⚠️  Missing: {missing}")


if __name__ == "__main__":
    asyncio.run(main())
