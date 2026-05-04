"""One-shot migration: copy rows from local SQLite into Supabase Postgres.

Run AFTER:
  1) db/schema.sql has been applied in Supabase SQL Editor
  2) `seed_forms_from_yaml()` has populated the `forms` table once
     (just start the app once with the new core/db.py)

Then run from the project root:

    .venv\\Scripts\\python.exe scripts\\migrate_sqlite_to_supabase.py

The script is idempotent for take_number/form_id pairs: it skips a take that
already exists in Postgres for the same (form_id, take_number).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.paths import DB_PATH  # noqa: E402
from core.db import conn        # noqa: E402  (Postgres conn)
from psycopg.types.json import Json  # noqa: E402


def _maybe_json(value):
    """SQLite stored TEXT; Postgres expects dict/list. Try to parse."""
    if value is None or value == "":
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value  # leave as-is if it isn't JSON


def migrate_takes(sqlite_conn, pg) -> int:
    rows = sqlite_conn.execute("SELECT * FROM reference_takes").fetchall()
    moved = 0
    for r in rows:
        existing = pg.execute(
            "SELECT id FROM reference_takes WHERE form_id=%s AND take_number=%s",
            (r["form_id"], r["take_number"]),
        ).fetchone()
        if existing:
            continue
        pg.execute(
            """INSERT INTO reference_takes
                (form_id, take_number, video_path, pose_path, overlay_path,
                 duration_sec, self_rating, notes, notes_lang, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                       COALESCE(%s::timestamptz, NOW()))""",
            (
                r["form_id"], r["take_number"], r["video_path"], r["pose_path"],
                r["overlay_path"], r["duration_sec"], r["self_rating"],
                r["notes"], r["notes_lang"], r["created_at"],
            ),
        )
        moved += 1
    return moved


def migrate_tests(sqlite_conn, pg) -> int:
    rows = sqlite_conn.execute("SELECT * FROM tests").fetchall()
    moved = 0
    for r in rows:
        pg.execute(
            """INSERT INTO tests
                (form_id, video_path, pose_path, overlay_path,
                 intent, intent_lang, expected, tags,
                 ai_score, ai_issues, detected_stances,
                 verdict, comment, comment_lang, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       %s, %s, %s, COALESCE(%s::timestamptz, NOW()))""",
            (
                r["form_id"], r["video_path"], r["pose_path"], r["overlay_path"],
                r["intent"], r["intent_lang"], r["expected"],
                Json(_maybe_json(r["tags"]) or []),
                r["ai_score"],
                Json(_maybe_json(r["ai_issues"]) or []),
                Json(_maybe_json(r["detected_stances"]) or []),
                r["verdict"], r["comment"], r["comment_lang"], r["created_at"],
            ),
        )
        moved += 1
    return moved


def migrate_feedback(sqlite_conn, pg) -> int:
    rows = sqlite_conn.execute("SELECT * FROM general_feedback").fetchall()
    moved = 0
    for r in rows:
        pg.execute(
            """INSERT INTO general_feedback
                (text, lang, resolved, resolution_note, created_at)
               VALUES (%s, %s, %s, %s, COALESCE(%s::timestamptz, NOW()))""",
            (
                r["text"], r["lang"], bool(r["resolved"]),
                r["resolution_note"], r["created_at"],
            ),
        )
        moved += 1
    return moved


def migrate_form_feedback(sqlite_conn, pg) -> int:
    """Carry over expert_feedback / status overrides per form."""
    rows = sqlite_conn.execute(
        "SELECT id, status, expert_feedback, expert_feedback_lang FROM forms"
    ).fetchall()
    moved = 0
    for r in rows:
        if not r["expert_feedback"] and r["status"] == "draft":
            continue
        pg.execute(
            """UPDATE forms
                  SET status=%s,
                      expert_feedback=%s,
                      expert_feedback_lang=%s,
                      updated_at=NOW()
                WHERE id=%s""",
            (
                r["status"] or "draft",
                r["expert_feedback"],
                r["expert_feedback_lang"] or "zh",
                r["id"],
            ),
        )
        moved += 1
    return moved


def main() -> None:
    if not DB_PATH.exists():
        print(f"No SQLite DB at {DB_PATH} — nothing to migrate.")
        return

    sqlite_conn = sqlite3.connect(DB_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    with conn() as pg:
        forms_count = pg.execute(
            "SELECT COUNT(*) AS n FROM forms"
        ).fetchone()["n"]
        if forms_count == 0:
            print(
                "Postgres `forms` table is empty. Start the app once first so "
                "seed_forms_from_yaml() populates it, then re-run this script."
            )
            return

        n_takes = migrate_takes(sqlite_conn, pg)
        n_tests = migrate_tests(sqlite_conn, pg)
        n_fb = migrate_feedback(sqlite_conn, pg)
        n_form_meta = migrate_form_feedback(sqlite_conn, pg)

    sqlite_conn.close()
    print(
        f"Migration complete: takes={n_takes}, tests={n_tests}, "
        f"feedback={n_fb}, form_meta_updates={n_form_meta}"
    )


if __name__ == "__main__":
    main()
