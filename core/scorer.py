"""Pose-sequence scoring: joint angles + DTW alignment vs reference."""
import math
from typing import Optional

import numpy as np


# MediaPipe landmark indices we care about
L = {
    "nose": 0,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
}

# Joints we monitor — (point1, vertex, point3) by landmark name
KEY_ANGLES = {
    "left_knee":   ("left_hip", "left_knee", "left_ankle"),
    "right_knee":  ("right_hip", "right_knee", "right_ankle"),
    "left_hip":    ("left_shoulder", "left_hip", "left_knee"),
    "right_hip":   ("right_shoulder", "right_hip", "right_knee"),
    "left_elbow":  ("left_shoulder", "left_elbow", "left_wrist"),
    "right_elbow": ("right_shoulder", "right_elbow", "right_wrist"),
}

# Display labels — bilingual via i18n keys instead would be nicer; here we keep raw
JOINT_DISPLAY = {
    "left_knee":   {"ko": "왼 무릎", "zh": "左膝"},
    "right_knee":  {"ko": "오른 무릎", "zh": "右膝"},
    "left_hip":    {"ko": "왼 엉덩이", "zh": "左髋"},
    "right_hip":   {"ko": "오른 엉덩이", "zh": "右髋"},
    "left_elbow":  {"ko": "왼 팔꿈치", "zh": "左肘"},
    "right_elbow": {"ko": "오른 팔꿈치", "zh": "右肘"},
}

JOINT_TOLERANCE_DEG = 15.0
ISSUE_THRESHOLD_DEG = 25.0
DTW_MAX_FRAMES = 600  # safety cap


def _angle(p1, p2, p3) -> Optional[float]:
    v1 = np.array([p1["x"] - p2["x"], p1["y"] - p2["y"], p1["z"] - p2["z"]])
    v2 = np.array([p3["x"] - p2["x"], p3["y"] - p2["y"], p3["z"] - p2["z"]])
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return None
    cos = float(np.dot(v1, v2) / (n1 * n2))
    cos = max(-1.0, min(1.0, cos))
    return math.degrees(math.acos(cos))


def frame_angles(landmarks) -> dict:
    """Per-frame dict {joint_name: degrees | None}."""
    if not landmarks:
        return {}
    out = {}
    for joint, (a, b, c) in KEY_ANGLES.items():
        try:
            la, lb, lc = landmarks[L[a]], landmarks[L[b]], landmarks[L[c]]
            if min(la["visibility"], lb["visibility"], lc["visibility"]) < 0.4:
                out[joint] = None
            else:
                out[joint] = _angle(la, lb, lc)
        except (IndexError, KeyError, TypeError):
            out[joint] = None
    return out


def angle_series(pose_seq: dict) -> list[dict]:
    return [frame_angles(f.get("landmarks")) for f in pose_seq.get("frames", [])]


def _frame_distance(fa: dict, fb: dict) -> float:
    diffs = []
    for k in KEY_ANGLES:
        a, b = fa.get(k), fb.get(k)
        if a is None or b is None:
            diffs.append(30.0)
        else:
            diffs.append(abs(a - b))
    return float(np.mean(diffs)) if diffs else 0.0


def _downsample(seq: list, max_n: int) -> list:
    if len(seq) <= max_n:
        return seq
    step = len(seq) / max_n
    return [seq[int(i * step)] for i in range(max_n)]


def _dtw(seq_a: list[dict], seq_b: list[dict]) -> tuple[list[tuple[int, int]], float]:
    """Standard DTW with backpointers. Returns aligned pairs and per-pair mean cost."""
    n, m = len(seq_a), len(seq_b)
    if n == 0 or m == 0:
        return [], float("inf")

    INF = float("inf")
    cost = np.full((n + 1, m + 1), INF, dtype=float)
    cost[0, 0] = 0.0
    parent = {}

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d = _frame_distance(seq_a[i - 1], seq_b[j - 1])
            choices = [
                (cost[i - 1, j - 1], (i - 1, j - 1)),
                (cost[i - 1, j],     (i - 1, j)),
                (cost[i, j - 1],     (i, j - 1)),
            ]
            best_val, best_par = min(choices, key=lambda x: x[0])
            cost[i, j] = d + best_val
            parent[(i, j)] = best_par

    pairs = []
    i, j = n, m
    while (i, j) in parent:
        pairs.append((i - 1, j - 1))
        i, j = parent[(i, j)]
    pairs.reverse()
    mean = cost[n, m] / max(1, len(pairs))
    return pairs, float(mean)


def score_against_reference(test_seq: dict, ref_seq: dict, lang: str = "ko") -> dict:
    """
    Compare test sequence to reference. Returns:
      total_score (0..10),
      mean_delta_deg,
      per_joint_mean_delta,
      issues: top deviations,
      frame_status_func: callable for visualizer overlay.
    """
    test_angles = angle_series(test_seq)
    ref_angles = angle_series(ref_seq)

    # Cap length for DTW performance (still aligns coarsely)
    test_capped = _downsample(test_angles, DTW_MAX_FRAMES)
    ref_capped = _downsample(ref_angles, DTW_MAX_FRAMES)
    test_idx_map = _index_map(len(test_angles), len(test_capped))
    ref_idx_map = _index_map(len(ref_angles), len(ref_capped))

    pairs_capped, mean_cost = _dtw(test_capped, ref_capped)

    # Map back to original indices
    pairs = [(test_idx_map[ti], ref_idx_map[ri]) for ti, ri in pairs_capped]

    per_joint: dict[str, list[float]] = {k: [] for k in KEY_ANGLES}
    issues: list[dict] = []
    fps = test_seq.get("fps") or 30.0

    test_frame_status: dict[int, dict[int, str]] = {}

    for ti, ri in pairs:
        if ti >= len(test_angles) or ri >= len(ref_angles):
            continue
        ta, ra = test_angles[ti], ref_angles[ri]
        joint_status = {}
        for joint_name, parts in KEY_ANGLES.items():
            t_val, r_val = ta.get(joint_name), ra.get(joint_name)
            if t_val is None or r_val is None:
                continue
            delta = abs(t_val - r_val)
            per_joint[joint_name].append(delta)
            sev = _severity_from_delta(delta)
            mid_idx = L[parts[1]]
            joint_status[mid_idx] = sev
            if delta >= ISSUE_THRESHOLD_DEG:
                issues.append({
                    "time_sec": round(ti / fps, 2),
                    "joint": joint_name,
                    "joint_label": JOINT_DISPLAY[joint_name].get(lang, joint_name),
                    "ref_deg": round(r_val, 1),
                    "test_deg": round(t_val, 1),
                    "delta_deg": round(delta, 1),
                    "severity": sev,
                })
        test_frame_status[ti] = joint_status

    # Worst issue per joint, then top 5
    by_joint: dict[str, dict] = {}
    for iss in issues:
        cur = by_joint.get(iss["joint"])
        if (cur is None) or iss["delta_deg"] > cur["delta_deg"]:
            by_joint[iss["joint"]] = iss
    top_issues = sorted(by_joint.values(), key=lambda x: -x["delta_deg"])[:5]

    score = max(0.0, 10.0 - mean_cost / 5.0)

    def frame_status_func(idx: int, landmarks):
        st = test_frame_status.get(idx)
        if not st:
            return None
        return {"joint_status": st, "label": None}

    return {
        "total_score": round(score, 2),
        "mean_delta_deg": round(mean_cost, 2),
        "per_joint_mean_delta": {
            k: round(float(np.mean(v)), 2) if v else None
            for k, v in per_joint.items()
        },
        "issues": top_issues,
        "frame_status_func": frame_status_func,
    }


def _index_map(orig_n: int, capped_n: int) -> list[int]:
    if capped_n >= orig_n:
        return list(range(orig_n))
    step = orig_n / capped_n
    return [int(i * step) for i in range(capped_n)]


def _severity_from_delta(delta: float) -> str:
    if delta < JOINT_TOLERANCE_DEG:
        return "ok"
    if delta < JOINT_TOLERANCE_DEG * 2:
        return "warn"
    return "bad"
