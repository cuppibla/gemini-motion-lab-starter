import json
import time
from typing import Any

from ..config import settings

MOCK_ANALYSIS: dict[str, Any] = {
    "movement_summary": (
        "A fluid upper body rotation with sweeping arm extension, "
        "demonstrating rhythmic side-to-side movement with strong core engagement."
    ),
    "body_parts": ["arms", "shoulders", "torso", "head"],
    "phases": [
        {
            "time_range": "0:00-0:01",
            "action": "Initial stance and weight shift",
            "tempo": "slow",
            "energy": "low",
        },
        {
            "time_range": "0:01-0:03",
            "action": "Core rotation with arm sweep",
            "tempo": "medium",
            "energy": "medium",
        },
        {
            "time_range": "0:03-0:05",
            "action": "Dynamic extension and return",
            "tempo": "fast",
            "energy": "high",
        },
    ],
    "camera_angle": "front-facing, medium shot",
    "overall_style": "fluid, rhythmic, energetic",
    "best_frame_timestamp": "0:02",
    "person_description": "person in casual attire performing fluid movement",
    "veo_prompt": (
        "A person performs fluid side-to-side upper body rotation with sweeping arm movements, "
        "rhythmic and energetic, front-facing medium shot, smooth motion, dynamic lighting."
    ),
}

_GEMINI_MODELS = [
    "gemini-3-flash-preview",
]


def analyze_video_sync(gcs_uri: str) -> dict[str, Any]:
    """Run Gemini motion analysis on the given GCS video URI.

    This is a synchronous function intended to be run in a thread via
    asyncio.to_thread().
    """
    if settings.MOCK_AI:
        time.sleep(5)
        return MOCK_ANALYSIS.copy()

    from google import genai
    from google.genai import types

    from ..prompts.motion_analysis import MOTION_ANALYSIS_PROMPT

    client = genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location="global",
    )

    last_error: Exception | None = None
    for model in _GEMINI_MODELS:
        try:
            mime_type = "video/mp4" if gcs_uri.lower().endswith(".mp4") else "video/webm"
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_uri(file_uri=gcs_uri, mime_type=mime_type),
                    MOTION_ANALYSIS_PROMPT,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    thinking_config=types.ThinkingConfig(thinking_budget=1024),
                ),
            )
            import logging
            logging.getLogger(__name__).info("Gemini model used: %s", model)
            return json.loads(response.text)
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("Gemini model %s failed: %s", model, exc)
            last_error = exc

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")
