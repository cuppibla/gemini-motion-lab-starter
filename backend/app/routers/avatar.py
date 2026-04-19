import asyncio
from fastapi import APIRouter, HTTPException
from ..models.schemas import GenerateAvatarRequest, GenerateAvatarResponse
from ..services import nano_banana_service, storage_service

router = APIRouter()


@router.post("/generate-avatar", response_model=GenerateAvatarResponse)
async def generate_avatar(request: GenerateAvatarRequest):
    # Load the extracted frame from GCS (saved during analysis step)
    try:
        frame_bytes = await asyncio.to_thread(storage_service.download_frame, request.video_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Frame not found for video_id={request.video_id}",
        )

    # Generate avatar image with Gemini 3 Pro Image (Nano Banana 2)
    image_bytes = await nano_banana_service.generate_avatar_image(
        frame_bytes, request.avatar_style
    )

    # Save generated avatar to GCS at gs://{BUCKET}/avatars/{video_id}.png
    gcs_uri = await asyncio.to_thread(
        storage_service.upload_avatar, request.video_id, image_bytes
    )

    # Generate a signed URL for the avatar image
    signed_url = await asyncio.to_thread(
        storage_service.generate_signed_url, gcs_uri, request.video_id
    )

    return GenerateAvatarResponse(avatar_image_url=signed_url)
