"""MediaPipe Pose extractor (Tasks API) — video → per-frame 33 keypoints."""
from pathlib import Path
import json
import os
from typing import Callable, Optional

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision

from .paths import DATA_DIR


LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear", "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_pinky", "right_pinky",
    "left_index", "right_index", "left_thumb", "right_thumb",
    "left_hip", "right_hip", "left_knee", "right_knee",
    "left_ankle", "right_ankle", "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
]

# MediaPipe Pose Landmarker connections (33-keypoint topology).
POSE_CONNECTIONS = [
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    # Torso
    (11, 12), (11, 23), (12, 24), (23, 24),
    # Left arm
    (11, 13), (13, 15),
    (15, 17), (15, 19), (15, 21), (17, 19),
    # Right arm
    (12, 14), (14, 16),
    (16, 18), (16, 20), (16, 22), (18, 20),
    # Left leg
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    # Right leg
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
]


def _model_path() -> Path:
    env = os.environ.get("WUSHU_POSE_MODEL")
    if env:
        return Path(env)
    return DATA_DIR / "models" / "pose_landmarker_full.task"


def _build_landmarker():
    model_path = _model_path()
    if not model_path.exists():
        raise FileNotFoundError(
            f"Pose model not found at {model_path}. "
            f"Run: python scripts/download_models.py"
        )
    base_options = mp_tasks.BaseOptions(model_asset_path=str(model_path))
    options = mp_vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False,
    )
    return mp_vision.PoseLandmarker.create_from_options(options)


def extract_pose_sequence(
    video_path: Path,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> dict:
    """
    Extract pose sequence from video using MediaPipe Tasks API.

    Returns dict:
        fps, width, height, frame_count, duration_sec,
        frames: list of { t: float, landmarks: list[33] | None }
    """
    video_path = Path(video_path)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count_hint = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    frames_data: list[dict] = []
    idx = 0

    landmarker = _build_landmarker()
    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int((idx / fps) * 1000) if fps else idx * 33
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            entry: dict = {"t": idx / fps if fps else 0.0, "landmarks": None}
            if result.pose_landmarks:
                lms = result.pose_landmarks[0]  # first detected pose
                entry["landmarks"] = [
                    {
                        "name": LANDMARK_NAMES[i],
                        "x": float(lm.x),
                        "y": float(lm.y),
                        "z": float(lm.z),
                        "visibility": float(getattr(lm, "visibility", 1.0) or 1.0),
                    }
                    for i, lm in enumerate(lms)
                ]
            frames_data.append(entry)
            idx += 1
            if progress_callback and frame_count_hint > 0 and idx % 5 == 0:
                progress_callback(min(0.99, idx / frame_count_hint))
    finally:
        landmarker.close()
        cap.release()

    if progress_callback:
        progress_callback(1.0)

    return {
        "fps": fps,
        "width": width,
        "height": height,
        "frame_count": idx,
        "duration_sec": (idx / fps) if fps else 0.0,
        "frames": frames_data,
    }


def save_pose_sequence(seq: dict, out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(seq, f)


def load_pose_sequence(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
