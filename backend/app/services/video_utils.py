import shutil
import subprocess
import tempfile
import cv2
import numpy as np  # noqa: F401  (kept for compatibility)


def _ffmpeg_exe() -> str | None:
    """Return path to an ffmpeg binary, preferring the imageio-ffmpeg bundle."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return shutil.which("ffmpeg")


def trim_video(input_path: str, duration_s: float) -> str:
    """Trim a video to the first duration_s seconds.

    Uses ffmpeg stream copy (no re-encode) when available; falls back to cv2
    frame-by-frame otherwise.  Returns the path to a new temp .mp4 file.
    The caller is responsible for deleting it.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.close()

    ffmpeg = _ffmpeg_exe()
    if ffmpeg:
        subprocess.run(
            [
                ffmpeg, "-y",
                "-i", input_path,
                "-t", str(duration_s),
                "-c", "copy",
                tmp.name,
            ],
            check=True,
            capture_output=True,
        )
        return tmp.name

    # cv2 fallback (may produce black frames if source codec is H.264)
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(tmp.name, fourcc, fps, (width, height))

    max_frames = int(duration_s * fps)
    frame_count = 0
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()
    return tmp.name


def compose_videos_side_by_side(original_path: str, generated_path: str) -> str:
    """Compose two videos vertically (9:16) — original on top, generated on bottom.

    Normalises both clips to 1080×960 (letterboxed) then vstacks them to
    produce a 1080×1920 H.264 MP4.  Returns the path to a new temp .mp4 file.
    The caller is responsible for deleting it.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    tmp.close()

    ffmpeg = _ffmpeg_exe()
    if ffmpeg:
        filter_complex = (
            "[0:v]scale=1080:960:force_original_aspect_ratio=decrease,"
            "pad=1080:960:(ow-iw)/2:(oh-ih)/2:color=black[top];"
            "[1:v]scale=1080:960:force_original_aspect_ratio=decrease,"
            "pad=1080:960:(ow-iw)/2:(oh-ih)/2:color=black[bot];"
            "[top][bot]vstack=inputs=2[out]"
        )
        cmd = [
            ffmpeg, "-y",
            "-i", original_path,
            "-i", generated_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "23",
            "-preset", "fast",
            "-movflags", "+faststart",
            "-t", "3",
            tmp.name,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return tmp.name
        except subprocess.CalledProcessError:
            # libx264 not available — retry with mpeg4
            cmd_fallback = [
                ffmpeg, "-y",
                "-i", original_path,
                "-i", generated_path,
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-c:v", "mpeg4",
                "-t", "3",
                tmp.name,
            ]
            subprocess.run(cmd_fallback, check=True, capture_output=True)
            return tmp.name

    raise RuntimeError("ffmpeg not available; cannot compose videos")


def _parse_timestamp(timestamp: str) -> float:
    """Parse timestamp string like '0:02' or '1:05' into seconds."""
    parts = timestamp.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(parts[0])


def extract_frame(video_path: str, timestamp: str) -> bytes:
    """Extract a single frame from a video at the given timestamp.

    Args:
        video_path: Local path to the video file.
        timestamp: Timestamp string like "0:02".

    Returns:
        PNG image as bytes.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    try:
        seconds = _parse_timestamp(timestamp)
    except (ValueError, IndexError):
        seconds = 2.5

    frame_number = int(seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    ret, frame = cap.read()
    if not ret:
        # Fallback: try frame at 2.5 seconds
        fallback_frame = int(2.5 * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, fallback_frame)
        ret, frame = cap.read()
        if not ret:
            cap.release()
            raise RuntimeError("Could not extract frame from video")

    cap.release()

    success, buffer = cv2.imencode(".png", frame)
    if not success:
        raise RuntimeError("Failed to encode frame as PNG")

    return buffer.tobytes()


def extract_storyboard_frames(
    video_path: str, interval_s: float = 0.5
) -> list[tuple[float, bytes]]:
    """Extract frames at regular intervals for storyboard analysis.

    Args:
        video_path: Local path to the video file.
        interval_s: Time between sampled frames in seconds.

    Returns:
        List of (timestamp_seconds, png_bytes) pairs.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    results: list[tuple[float, bytes]] = []
    t = 0.0
    while t <= duration + 0.01:
        frame_number = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if ret:
            ok, buf = cv2.imencode(".png", frame)
            if ok:
                results.append((round(t, 2), buf.tobytes()))
        t += interval_s

    cap.release()
    return results
