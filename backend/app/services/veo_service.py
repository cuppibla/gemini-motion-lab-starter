"""Veo video generation service.

Uses veo-3.1-generate-001 exclusively. If it fails, the error is surfaced
immediately so the user can retry — no silent fallback to lower-quality models.

When MOCK_AI=true the service returns a MockOperation that resolves after
~15 seconds of polling with a placeholder GCS URI.
"""

import asyncio
import logging
import time
import uuid
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory state (single-process; fine for a kiosk / demo deployment)
# ---------------------------------------------------------------------------

# operation_id → (operation_object, video_id)
_operations: dict[str, tuple[Any, str]] = {}

# operation_id → creation timestamp (used by MockOperation timing)
_mock_start_times: dict[str, float] = {}

# video_id → completed output GCS URI (populated when operation finishes)
_completed_videos: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Model fallback chain
# ---------------------------------------------------------------------------

_VEO_MODEL = "veo-3.1-fast-generate-001"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_video(
    avatar_image_gcs_uri: str,
    motion_analysis: dict[str, Any],
    avatar_style: str,
    location_theme: str,
    video_id: str,
) -> str:
    """Kick off a Veo video generation job.

    Returns an *operation_id* string that callers can pass to
    :func:`poll_operation` to check progress.
    """
    from ..prompts.video_generation import build_video_prompt

    op_id = str(uuid.uuid4())

    if settings.MOCK_AI:
        mock_op = _MockOperation(op_id)
        _operations[op_id] = (mock_op, video_id)
        _mock_start_times[op_id] = time.time()
        logger.info("MOCK_AI: created mock operation %s for video_id=%s", op_id, video_id)
        return op_id

    from google import genai
    from google.genai.types import GenerateVideosConfig, Image, VideoGenerationReferenceImage

    prompt = build_video_prompt(motion_analysis, avatar_style, location_theme)

    client = genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )

    operation = await _generate_with_retry(
        client=client,
        prompt=prompt,
        avatar_image_gcs_uri=avatar_image_gcs_uri,
        video_id=video_id,
    )
    logger.info("Veo model used: %s  operation_id=%s", _VEO_MODEL, op_id)
    _operations[op_id] = (operation, video_id)
    return op_id


_MAX_RETRIES = 3


async def _generate_with_retry(
    client: Any,
    prompt: str,
    avatar_image_gcs_uri: str,
    video_id: str,
) -> Any:
    """Attempt Veo generation up to _MAX_RETRIES times with exponential backoff."""
    import asyncio
    from google.genai.types import GenerateVideosConfig, Image, VideoGenerationReferenceImage

    _API_TIMEOUT_S = 120  # 2 min max per attempt

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            logger.info(
                "Veo attempt %d/%d with model %s (timeout=%ds)",
                attempt, _MAX_RETRIES, _VEO_MODEL, _API_TIMEOUT_S,
            )
            config = GenerateVideosConfig(
                reference_images=[
                    VideoGenerationReferenceImage(
                        image=Image(
                            gcs_uri=avatar_image_gcs_uri,
                            mime_type="image/png",
                        ),
                        reference_type="ASSET",
                    )
                ],
                aspect_ratio="16:9",
                duration_seconds=8,
                generate_audio=False,
                person_generation="allow_all",
                output_gcs_uri=f"gs://{settings.GCS_BUCKET}/output/{video_id}/",
            )
            operation = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_videos,
                    model=_VEO_MODEL,
                    prompt=prompt,
                    config=config,
                ),
                timeout=_API_TIMEOUT_S,
            )
            if attempt > 1:
                logger.info("Veo succeeded on attempt %d/%d", attempt, _MAX_RETRIES)
            return operation
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.exception(
                "Veo attempt %d/%d failed (%s): %r",
                attempt, _MAX_RETRIES, type(exc).__name__, exc,
            )
            if attempt < _MAX_RETRIES:
                delay = 2 ** (attempt - 1)  # 1s, 2s
                logger.info("Retrying Veo in %ds...", delay)
                await asyncio.sleep(delay)

    raise RuntimeError(f"Veo generation failed after {_MAX_RETRIES} attempts. Last error: {repr(last_error)}")


async def poll_operation(operation_id: str) -> dict[str, Any]:
    """Return the current status of a Veo operation.

    Returns a dict with keys:
      - ``status``:   "processing" | "complete" | "failed"
      - ``gcs_uri``:  output video GCS URI when complete, else None
      - ``video_id``: associated video_id
      - ``error``:    error message when failed, else None
    """
    entry = _operations.get(operation_id)
    if entry is None:
        return {
            "status": "failed",
            "gcs_uri": None,
            "video_id": None,
            "error": f"Unknown operation_id: {operation_id}",
        }

    operation, video_id = entry

    # ------------------------------------------------------------------
    # Mock path
    # ------------------------------------------------------------------
    if isinstance(operation, _MockOperation):
        elapsed = time.time() - _mock_start_times.get(operation_id, time.time())
        if elapsed < 15:
            return {
                "status": "processing",
                "gcs_uri": None,
                "video_id": video_id,
                "error": None,
            }
        gcs_uri = f"gs://{settings.GCS_BUCKET}/output/{video_id}/mock_video.mp4"
        _completed_videos[video_id] = gcs_uri
        return {
            "status": "complete",
            "gcs_uri": gcs_uri,
            "video_id": video_id,
            "error": None,
        }

    # ------------------------------------------------------------------
    # Real Veo operation — re-fetch via SDK to get current state
    # ------------------------------------------------------------------
    try:
        from google import genai

        client = genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT,
            location=settings.GOOGLE_CLOUD_LOCATION,
        )

        # Refresh the operation state from the backend (use sync in thread
        # to avoid httpx.ConnectError with the async transport)
        current_op = await asyncio.to_thread(client.operations.get, operation)

        if not current_op.done:
            return {
                "status": "processing",
                "gcs_uri": None,
                "video_id": video_id,
                "error": None,
            }

        # Check for error
        op_error = getattr(current_op, "error", None)
        if op_error and getattr(op_error, "code", 0):
            return {
                "status": "failed",
                "gcs_uri": None,
                "video_id": video_id,
                "error": getattr(op_error, "message", str(op_error)),
            }

        # Extract GCS URI from result using the official SDK pattern:
        # operation.result.generated_videos[0].video.uri
        result = getattr(current_op, "result", None)
        generated_videos = getattr(result, "generated_videos", None) if result else None
        if generated_videos:
            gcs_uri: str = generated_videos[0].video.uri
            _completed_videos[video_id] = gcs_uri
            return {
                "status": "complete",
                "gcs_uri": gcs_uri,
                "video_id": video_id,
                "error": None,
            }

        return {
            "status": "failed",
            "gcs_uri": None,
            "video_id": video_id,
            "error": f"No generated videos in operation result. error={op_error} result={result}",
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("Error polling operation %s: %s", operation_id, exc)
        return {
            "status": "failed",
            "gcs_uri": None,
            "video_id": video_id,
            "error": str(exc),
        }


def get_completed_video_uri(video_id: str) -> str | None:
    """Return the completed output GCS URI for a video_id, or None."""
    return _completed_videos.get(video_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _MockOperation:
    """Minimal stand-in for a real Veo AsyncOperation in MOCK_AI mode."""

    def __init__(self, name: str) -> None:
        self.name = name
