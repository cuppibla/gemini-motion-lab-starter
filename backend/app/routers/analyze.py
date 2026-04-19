import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ..config import settings
from ..services import gemini_service, storage_service, video_utils

router = APIRouter()

PHASE_MESSAGES = [
    "Uploading video for analysis...",
    "Detecting body landmarks...",
    "Analyzing motion patterns...",
    "Computing movement phases...",
    "Identifying style characteristics...",
]


@router.post("/analyze/{video_id}")
async def analyze_video(video_id: str):
    gcs_uri = f"gs://{settings.GCS_BUCKET}/uploads/{video_id}.webm"

    async def event_stream():
        # Kick off Gemini analysis in a background thread
        analysis_task = asyncio.create_task(
            asyncio.to_thread(gemini_service.analyze_video_sync, gcs_uri)
        )

        # Stream phase messages while analysis runs
        for msg in PHASE_MESSAGES:
            yield f"event: phase\ndata: {msg}\n\n"
            try:
                await asyncio.wait_for(asyncio.shield(analysis_task), timeout=1.0)
                break
            except asyncio.TimeoutError:
                pass

        try:
            analysis = await analysis_task
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"
            return

        # Best-effort: extract best frame and upload to GCS
        try:
            local_path = storage_service.download_to_temp(gcs_uri, video_id)
            timestamp = analysis.get("best_frame_timestamp", "0:02")
            frame_bytes = video_utils.extract_frame(local_path, timestamp)
            frame_uri = storage_service.upload_frame(video_id, frame_bytes)
            analysis["frame_uri"] = frame_uri
        except Exception:
            pass

        yield f"event: result\ndata: {json.dumps(analysis)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
