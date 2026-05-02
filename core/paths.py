"""Centralized filesystem paths for the workbench."""
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("WUSHU_DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()

VIDEOS_DIR = DATA_DIR / "videos"
REF_VIDEOS_DIR = VIDEOS_DIR / "references"
TEST_VIDEOS_DIR = VIDEOS_DIR / "tests"

POSES_DIR = DATA_DIR / "poses"
REF_POSES_DIR = POSES_DIR / "references"
TEST_POSES_DIR = POSES_DIR / "tests"

RENDERS_DIR = DATA_DIR / "renders"
REF_RENDERS_DIR = RENDERS_DIR / "references"
TEST_RENDERS_DIR = RENDERS_DIR / "tests"

TEMPLATES_DIR = DATA_DIR / "references"

DB_PATH = DATA_DIR / "workbench.db"
FORMS_YAML = DATA_DIR / "forms.yaml"
STANCE_YAML = DATA_DIR / "stance_dictionary.yaml"
I18N_DIR = DATA_DIR / "i18n"


def ensure_dirs() -> None:
    for d in (
        VIDEOS_DIR, REF_VIDEOS_DIR, TEST_VIDEOS_DIR,
        POSES_DIR, REF_POSES_DIR, TEST_POSES_DIR,
        RENDERS_DIR, REF_RENDERS_DIR, TEST_RENDERS_DIR,
        TEMPLATES_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
