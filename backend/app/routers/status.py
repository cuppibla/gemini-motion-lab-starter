import logging
import os

from fastapi import APIRouter

from ..models.schemas import StatusResponse
from ..services import veo_service, storage_service, video_utils

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache video_id → trimmed GCS URI to avoid re-trimming on repeated polls
_trimmed_uris: dict[str, str] = {}

_TRIM_DURATION_S = 3.0


@router.get("/status/{operation_id}", response_model=StatusResponse)
async def get_status(operation_id: str):
    result = await veo_service.poll_operation(operation_id)

    status = result["status"]

    if status == "processing":
        return StatusResponse(status="processing")

    if status == "failed":
        return StatusResponse(status="failed", error=result.get("error"))

    # status == "complete"
    gcs_uri: str | None = result.get("gcs_uri")
    video_id: str | None = result.get("video_id")

    if gcs_uri:
        # Return cached trimmed URI if already processed
        if video_id and video_id in _trimmed_uris:
            try:
                signed_url = storage_service.generate_video_signed_url(_trimmed_uris[video_id])
                return StatusResponse(status="complete", result_url=signed_url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Signed URL for trimmed video failed: %s", exc)

        # Download → trim to 3s → re-upload
        local_full: str | None = None
        local_trimmed: str | None = None
        try:
            local_full = storage_service.download_gcs_video(gcs_uri)
            local_trimmed = video_utils.trim_video(local_full, _TRIM_DURATION_S)

            with open(local_trimmed, "rb") as f:
                trimmed_data = f.read()

            trimmed_gcs_uri = storage_service.upload_trimmed_video(video_id, trimmed_data)
            if video_id:
                _trimmed_uris[video_id] = trimmed_gcs_uri

            signed_url = storage_service.generate_video_signed_url(trimmed_gcs_uri)
            return StatusResponse(status="complete", result_url=signed_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Video trim failed, falling back to full video: %s", exc)
        finally:
            for path in (local_full, local_trimmed):
                if path:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass

        # Fallback: serve the original 8s video
        try:
            signed_url = storage_service.generate_video_signed_url(gcs_uri)
            return StatusResponse(status="complete", result_url=signed_url)
        except Exception as exc:  # noqa: BLE001
            return StatusResponse(
                status="failed",
                error=f"Signed URL generation failed: {exc}",
            )

    # No GCS URI — this shouldn't happen; report failure so the user can retry
    return StatusResponse(
        status="failed",
        error="Video generation completed but no output was found. Please try again.",
    )
