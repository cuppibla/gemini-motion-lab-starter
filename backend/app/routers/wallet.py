"""Google Wallet pass generation for avatar cards."""

import base64
import io
import json
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..services import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _wallet_configured() -> bool:
    return bool(settings.GOOGLE_WALLET_ISSUER_ID and settings.GOOGLE_WALLET_SA_KEY_PATH)


def _compose_hero_banner(avatar_bytes: bytes) -> bytes:
    """Compose a 1032x336 wallet hero banner with the avatar on a branded background.

    Layout: gradient blue background, avatar on the left (with circular mask),
    and "Gemini Motion Lab" text + sparkle on the right.
    """
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    BANNER_W, BANNER_H = 1032, 336

    # Create gradient background (dark blue → Google blue)
    banner = Image.new("RGB", (BANNER_W, BANNER_H))
    draw = ImageDraw.Draw(banner)
    for x in range(BANNER_W):
        t = x / BANNER_W
        r = int(26 * (1 - t) + 66 * t)
        g = int(35 * (1 - t) + 133 * t)
        b = int(126 * (1 - t) + 244 * t)
        draw.line([(x, 0), (x, BANNER_H)], fill=(r, g, b))

    # Load and resize avatar
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar_size = int(BANNER_H * 0.75)  # 252px
    avatar = avatar.resize((avatar_size, avatar_size), Image.LANCZOS)

    # Create circular mask for avatar
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, avatar_size - 1, avatar_size - 1], fill=255)
    # Soften the edge slightly
    mask = mask.filter(ImageFilter.GaussianBlur(2))

    # Draw a subtle glow behind avatar
    glow_size = avatar_size + 20
    glow = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse([0, 0, glow_size - 1, glow_size - 1], fill=(255, 255, 255, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(10))

    # Position avatar on the left with padding
    avatar_x = 60
    avatar_y = (BANNER_H - avatar_size) // 2
    glow_x = avatar_x - 10
    glow_y = avatar_y - 10

    # Paste glow, then avatar
    banner.paste(
        glow.convert("RGB"),
        (glow_x, glow_y),
        glow.split()[3],
    )

    # Composite avatar with circular mask
    avatar_rgb = Image.new("RGB", (avatar_size, avatar_size), (0, 0, 0))
    avatar_rgb.paste(avatar, mask=avatar.split()[3] if avatar.mode == "RGBA" else None)
    banner.paste(avatar_rgb, (avatar_x, avatar_y), mask)

    # Add a thin white ring around the avatar circle
    ring_draw = ImageDraw.Draw(banner)
    ring_draw.ellipse(
        [avatar_x - 2, avatar_y - 2, avatar_x + avatar_size + 1, avatar_y + avatar_size + 1],
        outline=(255, 255, 255, 180),
        width=3,
    )

    # Add text — use a large built-in font
    text_x = avatar_x + avatar_size + 50
    text_y_center = BANNER_H // 2

    # Try to use a system font, fall back to default
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except (OSError, IOError):
        try:
            title_font = ImageFont.truetype("arial.ttf", 42)
            subtitle_font = ImageFont.truetype("arial.ttf", 24)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

    # Draw title
    draw = ImageDraw.Draw(banner)
    draw.text(
        (text_x, text_y_center - 45),
        "Gemini",
        fill=(255, 255, 255),
        font=title_font,
    )
    draw.text(
        (text_x, text_y_center - 5),
        "Motion Lab ✨",
        fill=(255, 255, 255),
        font=title_font,
    )

    # Draw subtitle
    draw.text(
        (text_x, text_y_center + 55),
        "Your AI Motion Avatar",
        fill=(200, 220, 255),
        font=subtitle_font,
    )

    # Save to bytes
    buf = io.BytesIO()
    banner.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _get_or_create_hero_banner(video_id: str) -> str:
    """Get the hero banner GCS URI, composing it from the avatar if needed."""
    hero_gcs_uri = f"gs://{settings.GCS_BUCKET}/avatars/{video_id}_wallet_hero.png"

    # Check if hero banner already exists
    if storage_service.gcs_blob_exists(hero_gcs_uri):
        return hero_gcs_uri

    # Download avatar, compose banner, upload
    avatar_gcs_uri = f"gs://{settings.GCS_BUCKET}/avatars/{video_id}.png"

    from google.cloud import storage as gcs

    client = gcs.Client(project=settings.GOOGLE_CLOUD_PROJECT)
    parts = avatar_gcs_uri.removeprefix("gs://").split("/", 1)
    bucket = client.bucket(parts[0])

    avatar_blob = bucket.blob(parts[1])
    avatar_bytes = avatar_blob.download_as_bytes()

    logger.info(f"Composing wallet hero banner for video_id={video_id}")
    hero_bytes = _compose_hero_banner(avatar_bytes)

    # Upload hero banner
    hero_parts = hero_gcs_uri.removeprefix("gs://").split("/", 1)
    hero_blob = bucket.blob(hero_parts[1])
    hero_blob.upload_from_string(hero_bytes, content_type="image/png")

    logger.info(f"Hero banner uploaded: {hero_gcs_uri} ({len(hero_bytes)} bytes)")
    return hero_gcs_uri


def _create_wallet_save_url(
    video_id: str,
    avatar_signed_url: str,
    hero_signed_url: str,
) -> str:
    """Create a Google Wallet 'Save' URL containing a signed JWT pass."""
    try:
        from google.auth import crypt as google_crypt
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="google-auth not installed — required for Google Wallet",
        )

    # Load service account key
    try:
        with open(settings.GOOGLE_WALLET_SA_KEY_PATH, "r") as f:
            sa_info = json.load(f)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Service account key not found: {settings.GOOGLE_WALLET_SA_KEY_PATH}",
        )

    issuer_id = settings.GOOGLE_WALLET_ISSUER_ID
    class_id = f"{issuer_id}.gemini_motion_lab"
    object_id = f"{issuer_id}.avatar_{video_id}_{uuid.uuid4().hex[:8]}"
    share_page_url = f"{settings.PUBLIC_BASE_URL}/share/{video_id}"

    # GenericClass — minimal
    generic_class = {"id": class_id}

    # GenericObject — the actual pass
    generic_object = {
        "id": object_id,
        "classId": class_id,
        "cardTitle": {
            "defaultValue": {"language": "en-US", "value": "Gemini Motion Lab"},
        },
        "subheader": {
            "defaultValue": {"language": "en-US", "value": "AI Motion Avatar"},
        },
        "header": {
            "defaultValue": {"language": "en-US", "value": "Your Avatar"},
        },
        # Hero banner (1032x336) — branded banner with avatar
        "heroImage": {
            "sourceUri": {"uri": hero_signed_url},
            "contentDescription": {
                "defaultValue": {"language": "en-US", "value": "Your AI avatar banner"},
            },
        },
        # Logo — avatar shown as circle in card header
        "logo": {
            "sourceUri": {"uri": avatar_signed_url},
            "contentDescription": {
                "defaultValue": {"language": "en-US", "value": "Avatar"},
            },
        },
        "textModulesData": [
            {
                "id": "date",
                "header": "Created",
                "body": time.strftime("%b %d, %Y"),
            },
            {
                "id": "type",
                "header": "Type",
                "body": "Motion Avatar",
            },
        ],
        "barcode": {
            "type": "QR_CODE",
            "value": share_page_url,
            "alternateText": "Scan to view video",
        },
        "hexBackgroundColor": "#1a237e",
    }

    # Build JWT payload
    now = int(time.time())
    origins = [settings.PUBLIC_BASE_URL, "*"]

    payload = {
        "iss": sa_info["client_email"],
        "aud": "google",
        "typ": "savetowallet",
        "iat": now,
        "origins": origins,
        "payload": {
            "genericClasses": [generic_class],
            "genericObjects": [generic_object],
        },
    }

    # Sign JWT with service account private key
    signer = google_crypt.RSASigner.from_service_account_info(sa_info)
    header = {"alg": "RS256", "typ": "JWT"}

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    signing_input = header_b64 + b"." + payload_b64
    signature = signer.sign(signing_input)
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=")

    jwt_token = (header_b64 + b"." + payload_b64 + b"." + signature_b64).decode()

    save_url = f"https://pay.google.com/gp/v/save/{jwt_token}"
    logger.info(f"Wallet save URL generated for video_id={video_id}")
    return save_url


@router.get("/share/{video_id}/wallet")
async def get_wallet_url(video_id: str):
    """Generate a Google Wallet save URL for the avatar pass."""
    if not _wallet_configured():
        raise HTTPException(
            status_code=501,
            detail="Google Wallet not configured. Set GOOGLE_WALLET_ISSUER_ID and GOOGLE_WALLET_SA_KEY_PATH.",
        )

    # Check avatar exists
    avatar_gcs_uri = f"gs://{settings.GCS_BUCKET}/avatars/{video_id}.png"
    if not storage_service.gcs_blob_exists(avatar_gcs_uri):
        raise HTTPException(
            status_code=404,
            detail=f"Avatar not found for video_id={video_id}",
        )

    try:
        # Compose hero banner (cached — only composed once per video)
        hero_gcs_uri = _get_or_create_hero_banner(video_id)

        # Generate signed URLs for both images
        avatar_signed_url = storage_service.generate_signed_url(avatar_gcs_uri, video_id)
        hero_signed_url = storage_service.generate_signed_url(hero_gcs_uri, video_id)

        save_url = _create_wallet_save_url(video_id, avatar_signed_url, hero_signed_url)
        return {"wallet_url": save_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create wallet URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Wallet error: {str(e)}")
