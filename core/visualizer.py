"""Skeleton overlay video renderer — points + connecting lines on each frame."""
from pathlib import Path
from typing import Callable, Optional

import cv2

from .pose_extractor import POSE_CONNECTIONS
from .scorer import KEY_ANGLES, L, frame_angles

# BGR colors
COLOR_OK = (120, 200, 100)
COLOR_WARN = (50, 200, 240)
COLOR_BAD = (60, 60, 220)
COLOR_NEUTRAL = (210, 210, 210)
COLOR_BG = (35, 28, 28)
COLOR_TEXT = (250, 245, 240)


def _color_for(severity: str):
    return {
        "ok": COLOR_OK,
        "warn": COLOR_WARN,
        "bad": COLOR_BAD,
        "neutral": COLOR_NEUTRAL,
    }.get(severity, COLOR_NEUTRAL)


def _max_severity(a: str, b: str) -> str:
    order = ["neutral", "ok", "warn", "bad"]
    ai = order.index(a) if a in order else 0
    bi = order.index(b) if b in order else 0
    return order[max(ai, bi)]


def _put_label(img, text: str, org: tuple, scale: float = 0.6) -> None:
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, 1)
    x, y = org
    cv2.rectangle(img, (x - 6, y - th - 6), (x + tw + 6, y + baseline + 2), COLOR_BG, -1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, scale, COLOR_TEXT, 1, cv2.LINE_AA)


def _draw_skeleton(img, landmarks, w: int, h: int, joint_status: Optional[dict] = None) -> None:
    if not landmarks:
        return
    js = joint_status or {}

    # Connections
    for a, b in POSE_CONNECTIONS:
        la, lb = landmarks[a], landmarks[b]
        if la["visibility"] < 0.3 or lb["visibility"] < 0.3:
            continue
        pa = (int(la["x"] * w), int(la["y"] * h))
        pb = (int(lb["x"] * w), int(lb["y"] * h))
        sev = _max_severity(js.get(a, "neutral"), js.get(b, "neutral"))
        cv2.line(img, pa, pb, _color_for(sev), 3, cv2.LINE_AA)

    # Joints
    for i, lm in enumerate(landmarks):
        if lm["visibility"] < 0.3:
            continue
        p = (int(lm["x"] * w), int(lm["y"] * h))
        sev = js.get(i, "neutral")
        cv2.circle(img, p, 5, _color_for(sev), -1, cv2.LINE_AA)
        cv2.circle(img, p, 6, (255, 255, 255), 1, cv2.LINE_AA)


# Pill backgrounds (BGR) — saturated colors that read on any video background
_PILL_BG = {
    "ok":      (70, 150, 60),    # green
    "warn":    (45, 130, 220),   # amber
    "bad":     (60, 60, 200),    # red
    "neutral": (40, 49, 160),    # brand wine #A03128
}


def _draw_angle_labels(img, landmarks, w: int, h: int, joint_status: Optional[dict] = None) -> None:
    """Draw each measured joint angle as a high-contrast colored pill badge.

    Pill size scales with frame resolution so the value stays readable when the
    video is shrunk to fit a narrow column in the UI. Targets ~3% of width.
    """
    if not landmarks:
        return
    js = joint_status or {}
    angles = frame_angles(landmarks)

    # Adaptive sizing — calibrated for 1280px wide frames.
    base = max(w, 720) / 1280.0
    font = cv2.FONT_HERSHEY_DUPLEX
    scale = max(0.95, 1.25 * base)
    thickness = max(2, int(round(2.4 * base)))
    pad_x = max(12, int(round(16 * base)))
    pad_y = max(8, int(round(11 * base)))
    border_w = max(2, int(round(2.2 * base)))
    shadow_off = max(3, int(round(4 * base)))
    leader_w = max(2, int(round(2.4 * base)))

    shadow = (0, 0, 0)
    border = (255, 255, 255)
    text_color = (255, 255, 255)

    for joint_name, (_, vertex_name, _) in KEY_ANGLES.items():
        deg = angles.get(joint_name)
        if deg is None:
            continue
        idx = L[vertex_name]
        lm = landmarks[idx]
        if lm["visibility"] < 0.4:
            continue
        cx = int(lm["x"] * w)
        cy = int(lm["y"] * h)
        sev = js.get(idx, "neutral")
        bg = _PILL_BG.get(sev, _PILL_BG["neutral"])

        text = f"{int(round(deg))}"
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)

        # Degree symbol drawn as a small open ring (HERSHEY fonts don't render Unicode °)
        deg_r = max(3, int(round(scale * 5)))
        deg_gap = max(3, int(round(scale * 4)))
        deg_total_w = deg_r * 2 + deg_gap

        # Anchor pill upper-right of joint, distance scales with size.
        offset_x = int(round(22 * base))
        offset_y = int(round(20 * base))
        ox = cx + offset_x
        oy = cy - offset_y
        x1, y1 = ox - pad_x, oy - th - pad_y
        x2, y2 = ox + tw + deg_total_w + pad_x, oy + baseline + pad_y - 2

        # Clamp inside frame
        margin = 4
        if x2 > w - margin:
            shift = x2 - (w - margin)
            x1 -= shift; x2 -= shift; ox -= shift
        if x1 < margin:
            shift = margin - x1
            x1 += shift; x2 += shift; ox += shift
        if y1 < margin:
            shift = margin - y1
            y1 += shift; y2 += shift; oy += shift
        if y2 > h - margin:
            shift = y2 - (h - margin)
            y1 -= shift; y2 -= shift; oy -= shift

        # Leader line from joint dot to pill — confirms which joint the value belongs to.
        pill_anchor_x = x1 if cx < (x1 + x2) // 2 else x2
        pill_anchor_y = y2 if cy > (y1 + y2) // 2 else y1
        cv2.line(img, (cx, cy), (pill_anchor_x, pill_anchor_y),
                 shadow, leader_w + 2, cv2.LINE_AA)
        cv2.line(img, (cx, cy), (pill_anchor_x, pill_anchor_y),
                 bg, leader_w, cv2.LINE_AA)

        # Drop shadow → solid pill → white border → white text
        cv2.rectangle(img, (x1 + shadow_off, y1 + shadow_off),
                      (x2 + shadow_off, y2 + shadow_off), shadow, -1, cv2.LINE_AA)
        cv2.rectangle(img, (x1, y1), (x2, y2), bg, -1, cv2.LINE_AA)
        cv2.rectangle(img, (x1, y1), (x2, y2), border, border_w, cv2.LINE_AA)
        cv2.putText(img, text, (ox, oy), font, scale, text_color, thickness, cv2.LINE_AA)
        # Degree symbol — small open ring at top-right of the number
        deg_cx = ox + tw + deg_gap + deg_r
        deg_cy = oy - th + deg_r
        cv2.circle(img, (deg_cx, deg_cy), deg_r, text_color,
                   max(1, thickness - 1), cv2.LINE_AA)


def render_overlay(
    video_path: Path,
    pose_seq: dict,
    out_path: Path,
    frame_status_func: Optional[Callable[[int, list], Optional[dict]]] = None,
    label_top: Optional[str] = None,
    show_angles: bool = True,
) -> Path:
    """
    Re-encode the input video with skeleton overlay drawn on each frame.

    frame_status_func(frame_idx, landmarks) -> { joint_status: {idx: 'ok'|'warn'|'bad'}, label: str }
    """
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    import imageio_ffmpeg

    cap = cv2.VideoCapture(str(video_path))
    fps = pose_seq.get("fps") or cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(pose_seq.get("width") or cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(pose_seq.get("height") or cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # H.264 / yuv420p so the resulting MP4 plays in every browser. (cv2's
    # default mp4v fourcc produces MPEG-4 Part 2, which Chrome / Firefox /
    # Safari refuse to play.) imageio-ffmpeg bundles its own ffmpeg binary
    # so we don't depend on apt installing one.
    writer = imageio_ffmpeg.write_frames(
        str(out_path),
        size=(w, h),
        fps=float(fps),
        codec="libx264",
        pix_fmt_in="bgr24",        # cv2 frames are BGR
        pix_fmt_out="yuv420p",     # required for browser playback
        macro_block_size=1,        # allow odd dimensions without auto-resize
        quality=7,                 # 0..10  (~CRF 23-ish at 7)
        ffmpeg_log_level="error",
    )
    writer.send(None)              # initialize the generator

    frames = pose_seq.get("frames", [])
    idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            landmarks = frames[idx].get("landmarks") if idx < len(frames) else None
            joint_status = None
            per_frame_label = None
            if frame_status_func and landmarks:
                res = frame_status_func(idx, landmarks)
                if res:
                    joint_status = res.get("joint_status")
                    per_frame_label = res.get("label")

            _draw_skeleton(frame, landmarks, w, h, joint_status)

            if show_angles and landmarks:
                _draw_angle_labels(frame, landmarks, w, h, joint_status)

            # Top-left timecode
            _put_label(frame, f"{idx / fps:5.2f}s", (12, 28), 0.55)

            # Top-right user label (e.g. take number)
            if label_top:
                (tw, th), _ = cv2.getTextSize(label_top, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
                _put_label(frame, label_top, (w - tw - 18, 28), 0.55)

            # Bottom-left per-frame label (e.g. detected stance)
            if per_frame_label:
                _put_label(frame, per_frame_label, (12, h - 16), 0.6)

            writer.send(frame)
            idx += 1
    finally:
        cap.release()
        writer.close()
    return out_path
