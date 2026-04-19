import tempfile
import os
from ..config import settings

# Map video_id → local temp file path (used in MOCK_AI mode)
_temp_files: dict[str, str] = {}
_frame_files: dict[str, str] = {}

# video_id → GCS URI for composed side-by-side video
_composed_cache: dict[str, str] = {}


def upload_video(video_id: str, data: bytes) -> str:
    """Upload video bytes to GCS. Returns gs:// URI."""
    gcs_uri = f"gs://{settings.GCS_BUCKET}/uploads/{video_id}.webm"

    if settings.MOCK_AI:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        tmp.write(data)
        tmp.close()
        _temp_files[video_id] = tmp.name
        return gcs_uri

    from google.cloud import storage as gcs

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(settings.GCS_BUCKET)
    blob = bucket.blob(f"uploads/{video_id}.webm")
    blob.upload_from_string(data, content_type="video/webm")
    return gcs_uri


def download_to_temp(gcs_uri: str, video_id: str) -> str:
    """Download video from GCS to a local temp file. Returns file path."""
    if settings.MOCK_AI:
        path = _temp_files.get(video_id)
        if path and os.path.exists(path):
            return path
        raise FileNotFoundError(f"No temp file found for video_id={video_id}")

    from google.cloud import storage as gcs

    parts = gcs_uri.removeprefix("gs://").split("/", 1)
    bucket_name, blob_path = parts[0], parts[1]

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    blob.download_to_filename(tmp.name)
    return tmp.name


def upload_frame(video_id: str, frame_data: bytes) -> str:
    """Upload PNG frame to GCS. Returns gs:// URI."""
    gcs_uri = f"gs://{settings.GCS_BUCKET}/frames/{video_id}.png"

    if settings.MOCK_AI:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.write(frame_data)
        tmp.close()
        _frame_files[video_id] = tmp.name
        return gcs_uri

    from google.cloud import storage as gcs

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(settings.GCS_BUCKET)
    blob = bucket.blob(f"frames/{video_id}.png")
    blob.upload_from_string(frame_data, content_type="image/png")
    return gcs_uri


def download_frame(video_id: str) -> bytes:
    """Download PNG frame from GCS. Returns raw bytes."""
    if settings.MOCK_AI:
        path = _frame_files.get(video_id)
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        # No frame stored yet in mock mode — return empty bytes so the service
        # can still exercise the code path without a real file.
        return b""

    from google.cloud import storage as gcs

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(settings.GCS_BUCKET)
    blob = bucket.blob(f"frames/{video_id}.png")
    return blob.download_as_bytes()


def upload_avatar(video_id: str, image_data: bytes) -> str:
    """Upload avatar PNG to GCS. Returns gs:// URI."""
    gcs_uri = f"gs://{settings.GCS_BUCKET}/avatars/{video_id}.png"

    if settings.MOCK_AI:
        return gcs_uri

    from google.cloud import storage as gcs

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(settings.GCS_BUCKET)
    blob = bucket.blob(f"avatars/{video_id}.png")
    blob.upload_from_string(image_data, content_type="image/png")
    return gcs_uri


def download_gcs_video(gcs_uri: str) -> str:
    """Download any GCS video to a local temp file. Returns file path.

    Not supported in MOCK_AI mode (raises FileNotFoundError).
    The caller is responsible for deleting the temp file.
    """
    if settings.MOCK_AI:
        raise FileNotFoundError("download_gcs_video not supported in MOCK_AI mode")

    from google.cloud import storage as gcs

    parts = gcs_uri.removeprefix("gs://").split("/", 1)
    bucket_name, blob_path = parts[0], parts[1]

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    blob.download_to_filename(tmp.name)
    return tmp.name


def upload_trimmed_video(video_id: str, data: bytes) -> str:
    """Upload trimmed video bytes to GCS. Returns gs:// URI."""
    gcs_uri = f"gs://{settings.GCS_BUCKET}/output/{video_id}/trimmed_3s.mp4"

    if settings.MOCK_AI:
        return gcs_uri

    from google.cloud import storage as gcs

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(settings.GCS_BUCKET)
    blob = bucket.blob(f"output/{video_id}/trimmed_3s.mp4")
    blob.upload_from_string(data, content_type="video/mp4")
    return gcs_uri


def gcs_blob_exists(gcs_uri: str) -> bool:
    """Return True if the GCS object exists, False otherwise."""
    if settings.MOCK_AI:
        return False

    from google.cloud import storage as gcs

    parts = gcs_uri.removeprefix("gs://").split("/", 1)
    bucket_name, blob_path = parts[0], parts[1]

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    blob = client.bucket(bucket_name).blob(blob_path)
    return blob.exists()


def upload_composed_video(video_id: str, data: bytes) -> str:
    """Upload composed side-by-side video bytes to GCS. Returns gs:// URI."""
    gcs_uri = f"gs://{settings.GCS_BUCKET}/output/{video_id}/composed.mp4"

    if settings.MOCK_AI:
        return gcs_uri

    from google.cloud import storage as gcs

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(settings.GCS_BUCKET)
    blob = bucket.blob(f"output/{video_id}/composed.mp4")
    blob.upload_from_string(data, content_type="video/mp4")
    return gcs_uri


def _signing_client():
    """Return a GCS client whose credentials support URL signing via IAM."""
    import google.auth
    from google.auth import impersonated_credentials
    from google.cloud import storage as gcs

    source_creds, _ = google.auth.default()
    signing_creds = impersonated_credentials.Credentials(
        source_credentials=source_creds,
        target_principal=settings.GCS_SIGNING_SA,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        lifetime=300,
    )
    return gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT, credentials=signing_creds)


def generate_signed_url(gcs_uri: str, video_id: str) -> str:
    """Generate a signed HTTPS URL for a GCS object (valid 1 hour)."""
    if settings.MOCK_AI:
        return f"https://storage.googleapis.com/{settings.GCS_BUCKET}/avatars/{video_id}.png?mock=true"

    import datetime

    parts = gcs_uri.removeprefix("gs://").split("/", 1)
    bucket_name, blob_path = parts[0], parts[1]

    client = _signing_client()
    blob = client.bucket(bucket_name).blob(blob_path)

    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(hours=1),
        method="GET",
    )


def generate_video_signed_url(gcs_uri: str) -> str:
    """Generate a signed HTTPS URL for a video GCS object (valid 24 hours)."""
    if settings.MOCK_AI:
        path = gcs_uri.removeprefix(f"gs://{settings.GCS_BUCKET}/")
        return f"https://storage.googleapis.com/{settings.GCS_BUCKET}/{path}?mock=true"

    import datetime

    parts = gcs_uri.removeprefix("gs://").split("/", 1)
    bucket_name, blob_path = parts[0], parts[1]

    client = _signing_client()
    blob = client.bucket(bucket_name).blob(blob_path)

    return blob.generate_signed_url(
        version="v4",
        expiration=datetime.timedelta(hours=24),
        method="GET",
        response_disposition='attachment; filename="my-motion-avatar.mp4"',
    )
