"""Initialize the workbench database and seed forms from YAML."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.db import init_db, seed_forms_from_yaml  # noqa: E402
from core.paths import ensure_dirs  # noqa: E402


def main() -> None:
    ensure_dirs()
    init_db()
    seed_forms_from_yaml()
    print("OK - database initialized and forms.yaml seeded into SQLite.")


if __name__ == "__main__":
    main()
