import asyncio
import base64
import logging
import time

from ..config import settings
from ..prompts.avatar_generation import build_avatar_prompt

logger = logging.getLogger(__name__)

# Minimal 1x1 transparent PNG for mock responses
_MOCK_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

# Reuse a single genai client (lazy-initialised)
_client = None


def _get_client():
    """Return a cached genai.Client singleton."""
    global _client
    if _client is None:
        import google.genai as genai

        _client = genai.Client(
            vertexai=settings.GOOGLE_GENAI_USE_VERTEXAI,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location="global",
        )
    return _client


async def generate_avatar_image(frame_bytes: bytes, style_key: str) -> bytes:
    """Generate a 1024x1024 avatar image using Gemini 2.5 Flash Image.

    Args:
        frame_bytes: PNG bytes of the extracted video frame (user's face/pose).
        style_key: Avatar style identifier (e.g. 'pixel-hero', 'cyber-nova').

    Returns:
        PNG image bytes of the generated avatar.
    """
    if settings.MOCK_AI:
        await asyncio.sleep(8)
        return _MOCK_PNG_BYTES

    prompt = build_avatar_prompt(style_key)

    from google.genai import types

    client = _get_client()

    image_part = types.Part.from_bytes(
        data=frame_bytes,
        mime_type="image/png",
    )

    t0 = time.perf_counter()

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-3.1-flash-image-preview",
        contents=[
            types.Content(
                role="user",
                parts=[
                    image_part,
                    types.Part.from_text(text=prompt),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            max_output_tokens=8192,
            response_modalities=["IMAGE"],
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            ],
            image_config=types.ImageConfig(
                aspect_ratio="1:1",
                output_mime_type="image/png",
            ),
        ),
    )

    elapsed = time.perf_counter() - t0

    for candidate in response.candidates:
        for part in candidate.content.parts:
            if part.inline_data is not None:
                size_kb = len(part.inline_data.data) / 1024
                logger.info(
                    "Avatar generated: style=%s size=%.0fKB time=%.1fs",
                    style_key, size_kb, elapsed,
                )
                return part.inline_data.data

    raise ValueError("Gemini returned no image in response")
