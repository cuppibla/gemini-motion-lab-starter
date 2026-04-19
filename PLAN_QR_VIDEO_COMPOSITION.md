# Plan: QR Code + Video Composition Feature

## Context
Building QR share + side-by-side video composition for a Google Cloud booth demo. Right now: local iteration only — no Dockerfile, no Cloud Run yet. Later: deploy to Cloud Run with a single Dockerfile before the booth event.

---

## Phase 1: Build the feature locally (this session)

### What the full flow looks like

```
User finishes on kiosk
        ↓
ShareScreen calls GET /api/share/{video_id}
        ↓
Backend composes original + generated → 9:16 vertical MP4
Uploads to GCS: output/{video_id}/composed.mp4
        ↓
Returns:
  download_url → 24hr signed GCS URL for composed.mp4
  qr_data      → http://localhost:8000/share/{video_id}   ← share page URL, not GCS URL
        ↓
Kiosk ShareScreen shows:
  • composed video preview (playing)
  • QR code encoding the share page URL
        ↓
User scans QR on phone (same WiFi during local dev)
        ↓
Phone browser opens: http://[local-ip]:8000/share/{video_id}
        ↓
Backend serves HTML page:
  • 9:16 composed video playing
  • "Share" button (Web Share API — works once on Cloud Run with HTTPS)
  • "Download" button (works locally)
  • "Post to X" link
```

### Video format: 9:16 vertical vstack (1080×1920)

```
┌──────────────┐
│              │
│     YOU      │  ← original recording (1080×960)
│   (original) │
│              │
├──────────────┤
│              │
│ YOUR AVATAR  │  ← AI generated (1080×960)
│  (generated) │
│              │
└──────────────┘
   1080 × 1920
```

**ffmpeg vstack filter:**

```bash
[0:v]scale=1080:960:force_original_aspect_ratio=decrease,
     pad=1080:960:(ow-iw)/2:(oh-ih)/2:color=black[top];
[1:v]scale=1080:960:force_original_aspect_ratio=decrease,
     pad=1080:960:(ow-iw)/2:(oh-ih)/2:color=black[bot];
[top][bot]vstack=inputs=2[out]
```

Output: 1080×1920 H.264 MP4, 3 seconds. Perfect for TikTok Reels, Instagram Reels/Stories.

---

### Files to change

#### 1. `backend/app/config.py`

Add one setting:

```python
PUBLIC_BASE_URL: str = "http://localhost:8000"
```

Used to build the share page URL in `qr_data`. Change to Cloud Run URL at deploy time via env var — no code change needed.

#### 2. `backend/app/services/video_utils.py`

Add `compose_videos_side_by_side(original_path: str, generated_path: str) -> str`:

- Uses existing `_ffmpeg_exe()` helper already in this file
- Applies vstack filter (9:16, 1080×1920)
- Tries `libx264` encoding; falls back to `mpeg4` on error (same defensive pattern as rest of file)
- Returns temp `.mp4` path — caller cleans up (same pattern as `trim_video()`)

#### 3. `backend/app/services/storage_service.py`

Add at module level:

```python
_composed_cache: dict[str, str] = {}   # video_id → GCS URI
```

Add `upload_composed_video(video_id: str, data: bytes) -> str`:

- Stores at `output/{video_id}/composed.mp4`
- Exact same pattern as existing `upload_trimmed_video()`
- `MOCK_AI` mode: returns mock URI (same pattern)

#### 4. `backend/app/routers/share.py`

**Two changes:**

**Update existing `GET /api/share/{video_id}` (JSON endpoint):**

1. Check `_composed_cache[video_id]` — if hit, skip composition
2. If miss:
   - a. Get trimmed GCS URI from `veo_service.get_completed_video_uri()`
   - b. Build original GCS URI: `gs://{bucket}/uploads/{video_id}.webm`
   - c. Download both to temp files (`download_to_temp`, `download_gcs_video`)
   - d. `compose_videos_side_by_side(original, trimmed)`
   - e. `upload_composed_video()`, cache GCS URI
   - f. Clean up temp files
3. Generate 24hr signed URL for `composed.mp4`
4. Return `ShareResponse`:
   - `download_url` = signed URL for composed.mp4
   - `qr_data` = `f"{settings.PUBLIC_BASE_URL}/share/{video_id}"`

**Add new `GET /share/{video_id}` (HTML endpoint):**

- Returns `HTMLResponse` with self-contained HTML page
- HTML page contains:
  - Mobile-optimized layout (viewport meta, dark bg)
  - `<video autoplay loop playsinline>` with the composed signed URL
  - "Share" button → Web Share API JS (fetches video blob, calls `navigator.share`)
  - "Download" button → `<a href=... download>`
  - "Post to X" → `window.open('https://twitter.com/intent/tweet?...')`
  - Fallback text if Web Share API not supported
- Internally calls the same composition logic to get the signed URL
- No template engine — inline f-string HTML is fine for a single page

#### 5. `frontend/src/screens/ShareScreen.tsx`

**Two additions:**

- **Loading state:** while `getShare()` is in-flight (composition takes ~3-5s first time), show a spinner/progress message instead of the QR. `qrcode.react` is already installed.
- **Composed video preview:** `<video autoPlay loop muted playsInline>` above the QR, using `data.download_url` (the signed URL for composed.mp4)
- `qr_data` now encodes the share page URL — the QR renders correctly with no other changes.

---

### Local dev QR testing

During local dev, QR encodes `http://localhost:8000/share/{video_id}`.

| Test scenario | How |
|---|---|
| Test share page works | Open `http://localhost:8000/share/{video_id}` in browser on same machine |
| Test on phone | Connect phone to same WiFi, use local IP: `http://192.168.x.x:8000/share/{video_id}` |
| Test Web Share API | Only works on HTTPS — defer to Cloud Run phase |

---

## Phase 2: Cloud Run deployment (later, before booth)

Do this separately when ready to deploy. **Not part of this session.**

| Task | Notes |
|---|---|
| Dockerfile | Single file: install system ffmpeg (`apt-get install -y ffmpeg`), build React frontend, install Python deps, serve everything from one FastAPI container |
| `main.py` | Mount `frontend/dist/` as StaticFiles for `/*` route |
| Cloud Run config | `--min-instances=1 --max-instances=1` — keeps warm, prevents in-memory state split |
| Env var | Set `PUBLIC_BASE_URL=https://[service].run.app` |
| GCS cleanup | Add lifecycle rule to delete `output/*/composed.mp4` after 7 days |

**Why `max-instances=1`:** All state (`_completed_videos`, `_composed_cache`) is in-memory. Multiple instances would each have their own memory — a `/share/{video_id}` request hitting the wrong instance returns 404. Single instance avoids this. For a booth with a queue (sequential users, not concurrent), 1 instance is plenty.

---

## Verification (Phase 1)

1. Run backend: `uv run uvicorn app.main:app --reload`
2. Complete a full generation run (or use `MOCK_AI=true`)
3. `GET /api/share/{video_id}` → confirm `download_url` points to composed.mp4, `qr_data` is a `/share/{video_id}` URL
4. Open `download_url` in browser → plays as 9:16 vertical video (original top, avatar bottom)
5. Open `GET /share/{video_id}` → HTML share page loads with video + buttons
6. Call `GET /api/share/{video_id}` again → should return instantly (cache hit, no recomposition)
7. On kiosk frontend: ShareScreen shows spinner during composition, then composed video + QR
