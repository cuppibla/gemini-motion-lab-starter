import logging
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from ..models.schemas import UploadResponse
from ..services import storage_service
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    video_id = str(uuid.uuid4())
    share_url = f"{settings.PUBLIC_BASE_URL}/share/{video_id}"
    print(f"\n{'='*60}")
    print(f"  NEW VIDEO: {video_id}")
    print(f"  Share page: {share_url}")
    print(f"{'='*60}\n")
    gcs_uri = storage_service.upload_video(video_id, data)

    return UploadResponse(video_id=video_id, gcs_uri=gcs_uri, share_url=share_url)
