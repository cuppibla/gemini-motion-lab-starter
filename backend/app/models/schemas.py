from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    video_id: str
    gcs_uri: str
    share_url: str


class MotionPhase(BaseModel):
    time_range: str
    action: str
    tempo: str
    energy: str


class AnalysisResult(BaseModel):
    movement_summary: str
    body_parts: list[str]
    phases: list[MotionPhase]
    camera_angle: str
    overall_style: str
    best_frame_timestamp: str
    person_description: str
    veo_prompt: str
    frame_uri: Optional[str] = None


class GenerateAvatarRequest(BaseModel):
    video_id: str
    avatar_style: str


class GenerateAvatarResponse(BaseModel):
    avatar_image_url: str


class GenerateVideoRequest(BaseModel):
    video_id: str
    avatar_image_url: str
    motion_analysis: dict
    avatar_style: str = "pixel-hero"
    location_theme: str = ""


class GenerateVideoResponse(BaseModel):
    operation_id: str


class StatusResponse(BaseModel):
    status: str
    result_url: Optional[str] = None
    error: Optional[str] = None


class ShareResponse(BaseModel):
    download_url: str
    qr_data: str


class ShareStatusResponse(BaseModel):
    stage: str  # "generating" | "composing" | "ready"
    download_url: Optional[str] = None
    avatar_url: Optional[str] = None
