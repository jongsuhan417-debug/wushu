"""Download MediaPipe Pose Landmarker model into data/models/."""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.paths import DATA_DIR  # noqa: E402


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
TARGET_NAME = "pose_landmarker_full.task"


def main() -> None:
    target_dir = DATA_DIR / "models"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / TARGET_NAME
    if target.exists():
        size = target.stat().st_size
        print(f"OK - already exists at {target}  ({size / 1024 / 1024:.1f} MB)")
        return
    print(f"Downloading from {MODEL_URL}")
    print(f"          to    {target}")
    urllib.request.urlretrieve(MODEL_URL, target)
    size = target.stat().st_size
    print(f"OK - downloaded ({size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
