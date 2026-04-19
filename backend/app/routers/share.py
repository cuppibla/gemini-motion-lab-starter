import logging
import os
import tempfile

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from ..config import settings
from ..models.schemas import ShareResponse, ShareStatusResponse
from ..services import storage_service, veo_service
from ..services.video_utils import compose_videos_side_by_side

logger = logging.getLogger(__name__)

# JSON API endpoint — mounted with /api prefix → /api/share/{video_id}
router = APIRouter()

# HTML share page — mounted without prefix → /share/{video_id}
html_router = APIRouter()


def _get_or_compose(video_id: str) -> str:
    """Return a 24hr signed URL for the composed video, composing it if needed.

    Returns a signed GCS URL string.
    Raises HTTPException on missing video or composition failure.
    """
    # 1. In-memory cache hit — fastest path
    if video_id in storage_service._composed_cache:
        gcs_uri = storage_service._composed_cache[video_id]
        return storage_service.generate_video_signed_url(gcs_uri)

    # 2. Composed video already in GCS (survives server restarts)
    composed_gcs_uri = f"gs://{settings.GCS_BUCKET}/output/{video_id}/composed.mp4"
    if storage_service.gcs_blob_exists(composed_gcs_uri):
        storage_service._composed_cache[video_id] = composed_gcs_uri
        return storage_service.generate_video_signed_url(composed_gcs_uri)

    # 3. Need to compose — find the trimmed generated video
    trimmed_gcs_uri = veo_service.get_completed_video_uri(video_id)
    if not trimmed_gcs_uri:
        # Server may have restarted — check GCS directly for the trimmed video
        trimmed_gcs_uri = f"gs://{settings.GCS_BUCKET}/output/{video_id}/trimmed_3s.mp4"
        if not storage_service.gcs_blob_exists(trimmed_gcs_uri):
            raise HTTPException(
                status_code=404,
                detail=f"No completed video found for video_id={video_id}",
            )

    # MOCK_AI: skip composition, return mock signed URL
    if settings.MOCK_AI:
        mock_uri = f"gs://{settings.GCS_BUCKET}/output/{video_id}/composed.mp4"
        storage_service._composed_cache[video_id] = mock_uri
        return storage_service.generate_video_signed_url(mock_uri)

    original_path: str | None = None
    generated_path: str | None = None
    composed_path: str | None = None

    try:
        # Download original webm
        original_gcs = f"gs://{settings.GCS_BUCKET}/uploads/{video_id}.webm"
        original_path = storage_service.download_to_temp(original_gcs, video_id)

        # Download trimmed generated mp4
        generated_path = storage_service.download_gcs_video(trimmed_gcs_uri)

        # Compose 9:16 vertical video
        composed_path = compose_videos_side_by_side(original_path, generated_path)

        # Upload to GCS and cache
        with open(composed_path, "rb") as f:
            composed_data = f.read()

        gcs_uri = storage_service.upload_composed_video(video_id, composed_data)
        storage_service._composed_cache[video_id] = gcs_uri

        return storage_service.generate_video_signed_url(gcs_uri)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Composition failed for video_id=%s: %s", video_id, exc)
        raise HTTPException(status_code=500, detail=f"Video composition failed: {exc}") from exc
    finally:
        for path in (original_path, generated_path, composed_path):
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass


@router.get("/share/{video_id}", response_model=ShareResponse)
async def get_share(video_id: str):
    """Return download URL for the composed video and a share page URL for the QR code."""
    try:
        signed_url = _get_or_compose(video_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate share URL: {exc}") from exc

    share_page_url = f"{settings.PUBLIC_BASE_URL}/share/{video_id}"
    return ShareResponse(download_url=signed_url, qr_data=share_page_url)


@router.get("/share/{video_id}/download")
async def download_video(video_id: str):
    """Same-origin proxy that streams the composed video with attachment headers.

    This fixes iOS Safari which ignores the HTML5 `download` attribute on
    cross-origin links (GCS signed URLs live on storage.googleapis.com).
    Works on all platforms: iOS Safari, Android Chrome, desktop browsers.
    """
    try:
        signed_url = _get_or_compose(video_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Download failed: {exc}") from exc

    async def _stream():
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", signed_url) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                    yield chunk

    return StreamingResponse(
        _stream(),
        media_type="video/mp4",
        headers={
            "Content-Disposition": 'attachment; filename="my-motion-avatar.mp4"',
        },
    )


@router.get("/share/{video_id}/status", response_model=ShareStatusResponse)
async def get_share_status(video_id: str):
    """Check video readiness — returns stage: generating | composing | ready."""

    def _get_avatar_url(vid: str) -> str | None:
        """Try to get a signed URL for the avatar image."""
        avatar_gcs = f"gs://{settings.GCS_BUCKET}/avatars/{vid}.png"
        try:
            if storage_service.gcs_blob_exists(avatar_gcs):
                return storage_service.generate_signed_url(avatar_gcs, vid)
        except Exception:  # noqa: BLE001
            pass
        return None

    # 1. Already composed? → ready
    if video_id in storage_service._composed_cache:
        gcs_uri = storage_service._composed_cache[video_id]
        try:
            signed_url = storage_service.generate_video_signed_url(gcs_uri)
            return ShareStatusResponse(
                stage="ready",
                download_url=signed_url,
                avatar_url=_get_avatar_url(video_id),
            )
        except Exception:  # noqa: BLE001
            pass

    composed_gcs_uri = f"gs://{settings.GCS_BUCKET}/output/{video_id}/composed.mp4"
    if storage_service.gcs_blob_exists(composed_gcs_uri):
        storage_service._composed_cache[video_id] = composed_gcs_uri
        try:
            signed_url = storage_service.generate_video_signed_url(composed_gcs_uri)
            return ShareStatusResponse(
                stage="ready",
                download_url=signed_url,
                avatar_url=_get_avatar_url(video_id),
            )
        except Exception:  # noqa: BLE001
            pass

    # 2. Trimmed or raw Veo output exists? → composing
    trimmed_gcs_uri = f"gs://{settings.GCS_BUCKET}/output/{video_id}/trimmed_3s.mp4"
    if storage_service.gcs_blob_exists(trimmed_gcs_uri):
        return ShareStatusResponse(stage="composing")

    raw_uri = veo_service.get_completed_video_uri(video_id)
    if raw_uri:
        return ShareStatusResponse(stage="composing")

    # 3. Nothing yet → generating
    return ShareStatusResponse(stage="generating")


@html_router.get("/share/{video_id}", response_class=HTMLResponse)
async def share_page(video_id: str):
    """Serve the mobile share landing page with stage-aware polling."""
    try:
        return _render_share_page(video_id)
    except Exception as exc:
        logger.exception("share_page failed for video_id=%s", video_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _render_share_page(video_id: str) -> HTMLResponse:
    api_status_url = f"/api/share/{video_id}/status"
    api_download_url = f"/api/share/{video_id}/download"
    wallet_api_url = f"/api/share/{video_id}/wallet"
    apple_wallet_api_url = f"/api/share/{video_id}/apple-wallet"
    wallet_enabled = "true" if settings.GOOGLE_WALLET_ISSUER_ID else "false"
    apple_wallet_enabled = "true" if settings.APPLE_PASS_TYPE_ID else "false"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#0A0A1A">
  <title>My Motion Avatar</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0A0A1A; color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      min-height: 100dvh; display: flex; flex-direction: column;
      align-items: center; padding: 24px 16px env(safe-area-inset-bottom, 16px); gap: 20px;
    }}
    h1 {{ font-size: 1.5rem; font-weight: 800; text-align: center; margin-top: 8px; }}
    p.sub {{ color: rgba(255,255,255,0.5); font-size: 0.9rem; text-align: center; }}
    video {{ width: 100%; max-width: 320px; border-radius: 16px; background: #111; aspect-ratio: 9/16; object-fit: cover; }}
    .buttons {{ display: flex; flex-direction: column; gap: 12px; width: 100%; max-width: 320px; }}
    a.btn {{
      display: flex; align-items: center; justify-content: center; gap: 8px;
      width: 100%; padding: 16px; border-radius: 50px; font-size: 1rem; font-weight: 700;
      border: none; cursor: pointer; text-decoration: none; -webkit-tap-highlight-color: transparent;
    }}
    .btn-save {{
      background: linear-gradient(135deg, #4285F4, #1a73e8); color: #fff;
    }}
    .btn-save-avatar {{
      background: rgba(255,255,255,0.1); color: #fff; border: 1px solid rgba(255,255,255,0.2);
    }}
    .btn-wallet {{
      background: #000; color: #fff; border: 1px solid rgba(255,255,255,0.15);
    }}
    .btn-apple-wallet {{
      background: #000; color: #fff; border: 1px solid rgba(255,255,255,0.15);
    }}
    .badge {{
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(66,133,244,0.15); border: 1px solid rgba(66,133,244,0.3);
      border-radius: 50px; padding: 6px 14px; font-size: 0.8rem; color: #4285F4;
    }}
    .avatar-section {{
      display: flex; align-items: center; gap: 16px;
      width: 100%; max-width: 320px; padding: 12px;
      background: rgba(255,255,255,0.05); border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
    }}
    .avatar-section img {{
      width: 80px; height: 80px; border-radius: 12px; object-fit: cover;
      border: 2px solid rgba(66,133,244,0.4);
    }}
    .avatar-section .info {{ flex: 1; }}
    .avatar-section .info p {{ color: rgba(255,255,255,0.7); font-size: 0.85rem; }}
    .avatar-section .info h3 {{ font-size: 1rem; font-weight: 700; margin-bottom: 2px; }}
    .loading {{ display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 40px 20px; }}
    .spinner {{
      width: 48px; height: 48px; border: 4px solid rgba(255,255,255,0.15);
      border-top-color: #4285F4; border-radius: 50%; animation: spin 1s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    @keyframes pulse {{ 0%,100% {{ opacity: 0.4; }} 50% {{ opacity: 1; }} }}
    .pulse {{ animation: pulse 1.8s ease-in-out infinite; }}
    .hidden {{ display: none !important; }}
    .stage-msg {{ color: rgba(255,255,255,0.6); font-size: 0.95rem; text-align: center; }}
    .stage-hint {{ color: rgba(255,255,255,0.35); font-size: 0.8rem; text-align: center; margin-top: 4px; }}
  </style>
</head>
<body>
  <span class="badge">\\u2728 Gemini Motion Lab</span>
  <h1>Your Motion Avatar</h1>
  <p class="sub">Original vs AI \\u2014 see the transformation</p>

  <div id="loading-state" class="loading">
    <div class="spinner"></div>
    <p id="stage-text" class="pulse stage-msg">
      Your video is being generated by AI...<br>This usually takes 1-2 minutes.
    </p>
    <p id="elapsed" style="color:rgba(255,255,255,0.3);font-size:0.8rem;margin-top:4px;font-variant-numeric:tabular-nums"></p>
    <p class="stage-hint">
      You can leave this page open --<br>your video will appear automatically!
    </p>
  </div>

  <!-- Timeout state -->
  <div id="timeout-state" class="loading hidden">
    <div style="font-size:3rem">&#x23F0;</div>
    <p style="color:#fff;font-size:1.1rem;font-weight:700;text-align:center">
      Your video session may have ended
    </p>
    <p style="color:rgba(255,255,255,0.5);font-size:0.85rem;text-align:center;max-width:260px">
      This can happen if the kiosk was restarted or the session timed out.
    </p>
    <p style="color:rgba(255,255,255,0.7);font-size:0.95rem;font-weight:600;text-align:center;margin-top:8px">
      Head back to the booth<br>and record again!
    </p>
  </div>

  <div id="ready-state" class="hidden">
    <video id="main-video" autoplay loop playsinline muted controls
      onerror="document.getElementById('video-error').style.display='flex'"></video>
    <div id="video-error" style="display:none;flex-direction:column;align-items:center;gap:12px;color:rgba(255,255,255,0.5);text-align:center;font-size:0.85rem;max-width:280px;">
      <span style="font-size:2rem">&#x26A0;&#xFE0F;</span>
      Video failed to load. Use the Save button below.
    </div>
  </div>

  <!-- Avatar section (shown when ready + avatar exists) -->
  <div id="avatar-section" class="avatar-section hidden">
    <img id="avatar-img" src="" alt="Your AI avatar">
    <div class="info">
      <h3>Your AI Avatar</h3>
      <p>Generated by Gemini</p>
    </div>
  </div>

  <div id="action-buttons" class="buttons hidden">
    <a class="btn btn-save" id="download-link" href="#" download="my-motion-avatar.mp4">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
      Save Video
    </a>
    <a class="btn btn-save-avatar hidden" id="avatar-download-link" href="#" download="my-avatar.png">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
      Save Avatar Image
    </a>
    <a class="btn btn-wallet hidden" id="wallet-link" href="#" target="_blank" rel="noopener">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M16 12h.01"/></svg>
      Add to Google Wallet
    </a>
    <a class="btn btn-apple-wallet hidden" id="apple-wallet-link" href="#">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M16 12h.01"/></svg>
      Add to Apple Wallet
    </a>
  </div>

  <script>
    const STATUS_URL = "{api_status_url}";
    const WALLET_URL = "{wallet_api_url}";
    const APPLE_WALLET_URL = "{apple_wallet_api_url}";
    const WALLET_ENABLED = {wallet_enabled};
    const APPLE_WALLET_ENABLED = {apple_wallet_enabled};
    let videoUrl = null;
    const stageText = document.getElementById('stage-text');
    const elapsedEl = document.getElementById('elapsed');
    const startTime = Date.now();

    const STAGE_MESSAGES = {{
      generating: 'Your video is being generated by AI...<br>This usually takes 1-2 minutes.',
      composing: 'Almost there!<br>Composing your final video...',
    }};

    // Stage-aware timeouts (milliseconds)
    const STAGE_TIMEOUTS = {{ generating: 5 * 60 * 1000, composing: 4 * 60 * 1000 }};
    let currentStage = 'generating';
    let stageStartTime = Date.now();

    function formatTime(ms) {{
      const s = Math.floor(ms / 1000);
      const m = Math.floor(s / 60);
      const sec = s % 60;
      return m + ':' + String(sec).padStart(2, '0');
    }}

    function showTimeout() {{
      document.getElementById('loading-state').classList.add('hidden');
      document.getElementById('timeout-state').classList.remove('hidden');
    }}

    async function pollForVideo() {{
      while (true) {{
        // Update elapsed timer
        elapsedEl.textContent = 'Waiting: ' + formatTime(Date.now() - startTime);

        // Check stage timeout
        const stageElapsed = Date.now() - stageStartTime;
        const limit = STAGE_TIMEOUTS[currentStage] || 5 * 60 * 1000;
        if (stageElapsed > limit) {{
          showTimeout();
          return;
        }}

        try {{
          const res = await fetch(STATUS_URL);
          if (res.ok) {{
            const data = await res.json();
            if (data.stage === 'ready' && data.download_url) {{
              showVideo(data.download_url, data.avatar_url);
              return;
            }}
            // Track stage transitions
            if (data.stage !== currentStage) {{
              currentStage = data.stage;
              stageStartTime = Date.now();
            }}
            if (STAGE_MESSAGES[data.stage]) {{
              stageText.innerHTML = STAGE_MESSAGES[data.stage];
            }}
          }}
        }} catch (e) {{ }}
        await new Promise(r => setTimeout(r, 2000));
      }}
    }}

    const DOWNLOAD_URL = "{api_download_url}";

    function showVideo(url, avatarUrl) {{
      videoUrl = url;
      document.getElementById('loading-state').classList.add('hidden');
      document.getElementById('ready-state').classList.remove('hidden');
      document.getElementById('action-buttons').classList.remove('hidden');
      document.getElementById('main-video').src = url;
      // Use same-origin proxy URL for download (fixes iOS Safari)
      document.getElementById('download-link').href = DOWNLOAD_URL;

      // Show avatar if available
      if (avatarUrl) {{
        document.getElementById('avatar-section').classList.remove('hidden');
        document.getElementById('avatar-img').src = avatarUrl;
        const avatarDl = document.getElementById('avatar-download-link');
        avatarDl.href = avatarUrl;
        avatarDl.classList.remove('hidden');
      }}

      // Fetch Google Wallet URL if enabled
      if (WALLET_ENABLED) {{
        fetch(WALLET_URL)
          .then(r => r.ok ? r.json() : null)
          .then(data => {{
            if (data && data.wallet_url) {{
              const walletLink = document.getElementById('wallet-link');
              walletLink.href = data.wallet_url;
              walletLink.classList.remove('hidden');
            }}
          }})
          .catch(() => {{}});
      }}

      // Show Apple Wallet button if enabled
      if (APPLE_WALLET_ENABLED) {{
        const appleLink = document.getElementById('apple-wallet-link');
        appleLink.href = APPLE_WALLET_URL;
        appleLink.classList.remove('hidden');
      }}
    }}

    pollForVideo();
  </script>
</body>
</html>"""

    return HTMLResponse(content=html)
