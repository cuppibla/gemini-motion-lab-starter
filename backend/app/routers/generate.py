import logging
from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models.schemas import GenerateVideoRequest, GenerateVideoResponse
from ..services import veo_service, pipeline
from . import queue as queue_tracker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate-video", response_model=GenerateVideoResponse)
async def generate_video(request: GenerateVideoRequest):
    # Derive avatar GCS URI from video_id (matches upload_avatar pattern)
    avatar_image_gcs_uri = (
        f"gs://{settings.GCS_BUCKET}/avatars/{request.video_id}.png"
    )

    avatar_style: str = request.avatar_style
    location_theme: str = request.location_theme

    logger.info(
        "generate-video called: video_id=%s avatar_style=%s location_theme=%s",
        request.video_id, avatar_style, location_theme,
    )

    try:
        operation_id = await veo_service.generate_video(
            avatar_image_gcs_uri=avatar_image_gcs_uri,
            motion_analysis=request.motion_analysis,
            avatar_style=avatar_style,
            location_theme=location_theme,
            video_id=request.video_id,
        )
    except Exception as exc:
        logger.exception("generate-video FAILED for video_id=%s", request.video_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    queue_tracker.register(request.video_id)

    # Only spawn pipeline if not already running for this video_id
    # (prevents duplicates from frontend retries)
    if not pipeline.is_running(request.video_id):
        pipeline.spawn(operation_id, request.video_id)

    return GenerateVideoResponse(operation_id=operation_id)
