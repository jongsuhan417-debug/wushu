"""Skeleton overlay video renderer — points + connecting lines on each frame."""
from pathlib import Path
from typing import Callable, Optional

import cv2

from .pose_extractor import POSE_CONNECTIONS

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


def render_overlay(
    video_path: Path,
    pose_seq: dict,
    out_path: Path,
    frame_status_func: Optional[Callable[[int, list], Optional[dict]]] = None,
    label_top: Optional[str] = None,
) -> Path:
    """
    Re-encode the input video with skeleton overlay drawn on each frame.

    frame_status_func(frame_idx, landmarks) -> { joint_status: {idx: 'ok'|'warn'|'bad'}, label: str }
    """
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    fps = pose_seq.get("fps") or cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(pose_seq.get("width") or cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(pose_seq.get("height") or cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, float(fps), (w, h))

    frames = pose_seq.get("frames", [])
    idx = 0
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

        # Top-left timecode
        _put_label(frame, f"{idx / fps:5.2f}s", (12, 28), 0.55)

        # Top-right user label (e.g. take number)
        if label_top:
            (tw, th), _ = cv2.getTextSize(label_top, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
            _put_label(frame, label_top, (w - tw - 18, 28), 0.55)

        # Bottom-left per-frame label (e.g. detected stance)
        if per_frame_label:
            _put_label(frame, per_frame_label, (12, h - 16), 0.6)

        writer.write(frame)
        idx += 1

    cap.release()
    writer.release()
    return out_path
