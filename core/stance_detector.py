"""Stance (步型) classifier — basic angle-based heuristic for v0.1."""
from .scorer import frame_angles


STANCE_LABELS = {
    "mabu":   {"ko": "마보", "zh": "马步"},
    "gongbu": {"ko": "궁보", "zh": "弓步"},
    "xubu":   {"ko": "허보", "zh": "虚步"},
    "pubu":   {"ko": "복보", "zh": "仆步"},
}


def detect_stance(landmarks) -> str | None:
    """Heuristic: classify the current frame as one of the 4 main stances or None."""
    if not landmarks:
        return None
    angles = frame_angles(landmarks)
    lk, rk = angles.get("left_knee"), angles.get("right_knee")
    if lk is None or rk is None:
        return None

    # Mabu — both knees deeply bent
    if 70 <= lk <= 110 and 70 <= rk <= 110 and abs(lk - rk) < 25:
        return "mabu"
    # Gongbu — one knee bent, one straight
    if (60 <= lk <= 115 and rk > 155) or (60 <= rk <= 115 and lk > 155):
        return "gongbu"
    # Xubu — back knee bent, front knee mostly straight (subtle)
    if (75 <= lk <= 115 and 140 <= rk <= 175) or (75 <= rk <= 115 and 140 <= lk <= 175):
        return "xubu"
    # Pubu — extreme split
    if (lk < 50 and rk > 160) or (rk < 50 and lk > 160):
        return "pubu"
    return None


def detect_stance_sequence(pose_seq: dict, debounce_sec: float = 0.4) -> list[dict]:
    """Return list of {time_sec, stance} when a different stance is detected (debounced)."""
    fps = pose_seq.get("fps") or 30.0
    out = []
    last_stance = None
    last_t = -1.0
    for i, f in enumerate(pose_seq.get("frames", [])):
        st = detect_stance(f.get("landmarks"))
        t = i / fps
        if st and st != last_stance and (t - last_t) >= debounce_sec:
            out.append({"time_sec": round(t, 2), "stance": st})
            last_stance = st
            last_t = t
    return out


def stance_label(key: str, lang: str) -> str:
    return STANCE_LABELS.get(key, {}).get(lang, key)
