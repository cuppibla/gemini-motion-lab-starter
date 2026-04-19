"""MediaPipe-based pose extraction and motion event detection.

Produces a structured motion transcript from a video:
  - Per-frame joint angles sampled at SAMPLE_FPS
  - Velocity labels between frames (hold / slow / medium / fast / snap)
  - Key motion events (wrist peaks, direction reversals, body lean peaks)
  - Human-readable summaries for Gemini context and Veo prompts
"""

import logging
import math

import cv2

logger = logging.getLogger(__name__)

SAMPLE_FPS = 5  # frames per second to analyse


# ─── Public API ───────────────────────────────────────────────────────────────


def extract_pose_transcript(video_path: str) -> dict:
    """Extract skeletal pose data from a video file.

    Returns:
        {
            "keyframes":     list of {t, joints, velocity_label},
            "motion_events": list of {t, type, description},
            "duration":      float (seconds),
        }
    """
    try:
        import mediapipe as mp
    except ImportError:
        logger.warning("mediapipe not installed — pose extraction skipped")
        return {"keyframes": [], "motion_events": [], "duration": 0.0}

    mp_pose = mp.solutions.pose

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / video_fps
    frame_step = max(1, round(video_fps / SAMPLE_FPS))

    raw: list[dict] = []

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_step == 0:
                t = round(frame_idx / video_fps, 2)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)
                if result.pose_landmarks:
                    lm = result.pose_landmarks.landmark
                    raw.append({"t": t, "joints": _extract_joints(lm)})
                else:
                    logger.debug("No pose detected at t=%.2fs", t)
            frame_idx += 1

    cap.release()

    if not raw:
        logger.warning("Pose extraction produced no keyframes for %s", video_path)
        return {"keyframes": [], "motion_events": [], "duration": round(duration, 2)}

    keyframes = _annotate_velocity(raw)
    motion_events = _detect_motion_events(keyframes)

    logger.info(
        "Pose: %d keyframes, %d events, duration=%.2fs",
        len(keyframes), len(motion_events), duration,
    )
    return {
        "keyframes": keyframes,
        "motion_events": motion_events,
        "duration": round(duration, 2),
    }


def format_pose_summary(transcript: dict) -> str:
    """Format a pose transcript as a concise text table for Gemini's context.

    Gemini uses this to produce more accurately timestamped veo_prompt output.
    """
    keyframes = transcript.get("keyframes", [])
    events = transcript.get("motion_events", [])
    if not keyframes:
        return ""

    lines = [
        "SKELETAL POSE DATA (computer-vision ground truth, sampled at 5 fps):",
        "Use these measurements to ensure your timestamps are precise.",
        "",
        "Time  | R-arm° | L-arm° | R-wristH | L-wristH | Spine°  | Speed",
        "------|--------|--------|----------|----------|---------|------",
    ]
    for kf in keyframes:
        j = kf["joints"]
        lines.append(
            f"{kf['t']:5.2f}s"
            f" | {j.get('r_arm_raise', 0):6}°"
            f" | {j.get('l_arm_raise', 0):6}°"
            f" | {j.get('r_wrist_y', 0):8.2f}"
            f" | {j.get('l_wrist_y', 0):8.2f}"
            f" | {j.get('spine_tilt', 0):+7.1f}°"
            f" | {kf.get('velocity_label', '-')}"
        )

    if events:
        lines.append("")
        lines.append("Detected motion events:")
        for ev in events:
            lines.append(f"  t={ev['t']:.2f}s  [{ev['type']}]  {ev['description']}")

    return "\n".join(lines)


def format_keyframes_for_veo(keyframes: list[dict], motion_events: list[dict]) -> str:
    """Convert pose keyframes to a natural-language timestamped motion script
    for direct inclusion in the Veo generation prompt.

    Example output:
        [0.0s] right arm at side, left arm at side — hold
        [0.5s] right arm lifted low-forward, left arm at side — slow
        [1.0s] right arm raised to chest height — medium
        [1.5s] right arm fully overhead  ★ right hand reaches highest point
        [2.0s] right arm overhead, body leaning left — snap
    """
    if not keyframes:
        return ""

    event_map: dict[float, str] = {ev["t"]: ev["description"] for ev in (motion_events or [])}

    lines: list[str] = []
    for kf in keyframes:
        t = kf["t"]
        desc_parts = _describe_pose(kf.get("joints", {}))
        description = ", ".join(desc_parts) if desc_parts else "neutral position"
        vel = kf.get("velocity_label", "")
        speed = f" — {vel}" if vel and vel != "hold" else ""
        annotation = f"  ★ {event_map[t]}" if t in event_map else ""
        lines.append(f"[{t:.1f}s] {description}{speed}{annotation}")

    return "\n".join(lines)


# ─── Joint extraction ─────────────────────────────────────────────────────────


def _extract_joints(lm) -> dict:
    """Extract key joint angles and positions from MediaPipe Pose landmarks."""
    return {
        # Arm raise angle at the shoulder (0° = arm at side, 180° = straight up).
        # Computed as the angle at the shoulder landmark between the hip and elbow.
        "r_arm_raise": round(_angle(lm, 24, 12, 14)),  # r_hip → r_shoulder → r_elbow
        "l_arm_raise": round(_angle(lm, 23, 11, 13)),  # l_hip → l_shoulder → l_elbow

        # Elbow flexion (180° = fully extended, ~90° = right-angle bend)
        "r_elbow": round(_angle(lm, 12, 14, 16)),  # r_shoulder → r_elbow → r_wrist
        "l_elbow": round(_angle(lm, 11, 13, 15)),  # l_shoulder → l_elbow → l_wrist

        # Wrist height normalised to frame height (1.0 = top, 0.0 = bottom)
        "r_wrist_y": round(1.0 - lm[16].y, 3),
        "l_wrist_y": round(1.0 - lm[15].y, 3),

        # Wrist horizontal position (0.0 = left edge, 1.0 = right edge)
        "r_wrist_x": round(lm[16].x, 3),
        "l_wrist_x": round(lm[15].x, 3),

        # Hip extension (torso lean / squat depth)
        "r_hip_bend": round(_angle(lm, 12, 24, 26)),  # r_shoulder → r_hip → r_knee
        "l_hip_bend": round(_angle(lm, 11, 23, 25)),  # l_shoulder → l_hip → l_knee

        # Spine lateral tilt (positive = leans right, negative = leans left)
        "spine_tilt": round(_spine_tilt(lm), 1),
    }


def _angle(lm, a: int, b: int, c: int) -> float:
    """Angle in degrees at vertex b formed by the triangle a–b–c."""
    ax, ay = lm[a].x, lm[a].y
    bx, by = lm[b].x, lm[b].y
    cx, cy = lm[c].x, lm[c].y
    v1 = (ax - bx, ay - by)
    v2 = (cx - bx, cy - by)
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag = math.sqrt(v1[0] ** 2 + v1[1] ** 2) * math.sqrt(v2[0] ** 2 + v2[1] ** 2)
    if mag == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / mag))))


def _spine_tilt(lm) -> float:
    """Lateral spine tilt in degrees. Positive = leaning right."""
    sh_x = (lm[11].x + lm[12].x) / 2
    sh_y = (lm[11].y + lm[12].y) / 2
    hi_x = (lm[23].x + lm[24].x) / 2
    hi_y = (lm[23].y + lm[24].y) / 2
    dx = sh_x - hi_x
    # hi_y > sh_y because image y increases downward; invert so spine points "up"
    dy = hi_y - sh_y
    if dy == 0:
        return 0.0
    return math.degrees(math.atan2(dx, dy))


# ─── Velocity annotation ──────────────────────────────────────────────────────


def _annotate_velocity(keyframes: list[dict]) -> list[dict]:
    """Label each keyframe with a speed category based on wrist displacement."""
    if not keyframes:
        return []

    result = [dict(keyframes[0], velocity_label="hold")]
    for i in range(1, len(keyframes)):
        prev_j = keyframes[i - 1]["joints"]
        curr = keyframes[i]
        curr_j = curr["joints"]
        dt = curr["t"] - keyframes[i - 1]["t"]
        if dt <= 0:
            result.append(dict(curr, velocity_label="hold"))
            continue

        # Maximum positional displacement across all four wrist coordinates
        delta = max(
            abs(curr_j["r_wrist_y"] - prev_j["r_wrist_y"]),
            abs(curr_j["l_wrist_y"] - prev_j["l_wrist_y"]),
            abs(curr_j["r_wrist_x"] - prev_j["r_wrist_x"]),
            abs(curr_j["l_wrist_x"] - prev_j["l_wrist_x"]),
        )
        speed = delta / dt

        if speed < 0.04:
            label = "hold"
        elif speed < 0.15:
            label = "slow"
        elif speed < 0.35:
            label = "medium"
        elif speed < 0.7:
            label = "fast"
        else:
            label = "snap"

        result.append(dict(curr, velocity_label=label))

    return result


# ─── Motion event detection ───────────────────────────────────────────────────


def _detect_motion_events(keyframes: list[dict]) -> list[dict]:
    """Identify discrete motion events: wrist peaks, direction reversals, body lean peaks."""
    if len(keyframes) < 3:
        return []

    events: list[dict] = []

    for i in range(1, len(keyframes) - 1):
        prev_j = keyframes[i - 1]["joints"]
        curr = keyframes[i]
        curr_j = curr["joints"]
        next_j = keyframes[i + 1]["joints"]
        t = curr["t"]

        # ── Wrist vertical peaks (arm fully raised) ──────────────────────────
        if (curr_j["r_wrist_y"] > prev_j["r_wrist_y"]
                and curr_j["r_wrist_y"] > next_j["r_wrist_y"]
                and curr_j["r_wrist_y"] > 0.55):
            events.append({
                "t": t, "type": "r_wrist_peak",
                "description": f"right hand reaches highest point (h={curr_j['r_wrist_y']:.2f})",
            })

        if (curr_j["l_wrist_y"] > prev_j["l_wrist_y"]
                and curr_j["l_wrist_y"] > next_j["l_wrist_y"]
                and curr_j["l_wrist_y"] > 0.55):
            events.append({
                "t": t, "type": "l_wrist_peak",
                "description": f"left hand reaches highest point (h={curr_j['l_wrist_y']:.2f})",
            })

        # ── Lateral direction reversals ───────────────────────────────────────
        dx_prev = curr_j["r_wrist_x"] - prev_j["r_wrist_x"]
        dx_next = next_j["r_wrist_x"] - curr_j["r_wrist_x"]
        if abs(dx_prev) > 0.04 and abs(dx_next) > 0.04 and dx_prev * dx_next < 0:
            direction = "right" if dx_next > 0 else "left"
            events.append({
                "t": t, "type": "r_hand_reversal",
                "description": f"right hand reverses direction, now moving {direction}",
            })

        dx_prev_l = curr_j["l_wrist_x"] - prev_j["l_wrist_x"]
        dx_next_l = next_j["l_wrist_x"] - curr_j["l_wrist_x"]
        if abs(dx_prev_l) > 0.04 and abs(dx_next_l) > 0.04 and dx_prev_l * dx_next_l < 0:
            direction = "right" if dx_next_l > 0 else "left"
            events.append({
                "t": t, "type": "l_hand_reversal",
                "description": f"left hand reverses direction, now moving {direction}",
            })

        # ── Spine tilt peak (maximum body lean) ──────────────────────────────
        tilt = curr_j["spine_tilt"]
        if (abs(tilt) > abs(prev_j["spine_tilt"])
                and abs(tilt) > abs(next_j["spine_tilt"])
                and abs(tilt) > 10):
            direction = "right" if tilt > 0 else "left"
            events.append({
                "t": t, "type": "body_lean_peak",
                "description": f"maximum body lean {direction} ({abs(tilt):.0f}°)",
            })

    return sorted(events, key=lambda e: e["t"])


# ─── Natural-language pose description ───────────────────────────────────────


def _describe_pose(joints: dict) -> list[str]:
    """Convert joint angles into natural-language pose tokens."""
    parts: list[str] = []

    r_arm = joints.get("r_arm_raise", 0)
    l_arm = joints.get("l_arm_raise", 0)
    r_elbow = joints.get("r_elbow", 180)
    spine = joints.get("spine_tilt", 0)
    r_wx = joints.get("r_wrist_x", 0.5)
    l_wx = joints.get("l_wrist_x", 0.5)

    # Right arm height
    if r_arm < 25:
        parts.append("right arm at side")
    elif r_arm < 55:
        parts.append("right arm lifted forward (low)")
    elif r_arm < 95:
        parts.append("right arm at chest/shoulder height")
    elif r_arm < 135:
        parts.append("right arm raised high")
    else:
        parts.append("right arm fully overhead")

    # Right elbow bend (only mention when arm is raised and elbow is significantly bent)
    if r_arm > 35 and r_elbow < 130:
        parts.append(f"elbow bent {r_elbow:.0f}°")

    # Left arm height
    if l_arm < 25:
        parts.append("left arm at side")
    elif l_arm < 95:
        parts.append("left arm raised")
    else:
        parts.append("left arm overhead")

    # Wide lateral spread
    if abs(r_wx - l_wx) > 0.5:
        parts.append("arms spread wide")

    # Spine lean
    if abs(spine) > 12:
        direction = "right" if spine > 0 else "left"
        parts.append(f"body leaning {direction}")

    return parts
