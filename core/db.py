"""SQLite persistence for forms, reference takes, and tests."""
import sqlite3
import json
from contextlib import contextmanager
from typing import Optional, Iterable

import yaml

from .paths import DB_PATH, FORMS_YAML, ensure_dirs


SCHEMA = """
CREATE TABLE IF NOT EXISTS forms (
    id TEXT PRIMARY KEY,
    dan_level INTEGER NOT NULL,
    name_ko TEXT NOT NULL,
    name_zh TEXT NOT NULL,
    name_en TEXT,
    duration_sec_estimate INTEGER,
    description_ko TEXT,
    description_zh TEXT,
    primary_stances TEXT,
    weapon_category TEXT,
    ai_guidelines TEXT,             -- JSON: {source, verified_facts, pending}
    expert_feedback TEXT,
    expert_feedback_lang TEXT DEFAULT 'zh',
    status TEXT DEFAULT 'draft',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reference_takes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id TEXT NOT NULL,
    take_number INTEGER NOT NULL,
    video_path TEXT NOT NULL,
    pose_path TEXT NOT NULL,
    overlay_path TEXT,
    duration_sec REAL,
    self_rating INTEGER,
    notes TEXT,
    notes_lang TEXT DEFAULT 'zh',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    form_id TEXT NOT NULL,
    video_path TEXT NOT NULL,
    pose_path TEXT,
    overlay_path TEXT,
    intent TEXT,
    intent_lang TEXT DEFAULT 'zh',
    expected TEXT,
    tags TEXT,
    ai_score REAL,
    ai_issues TEXT,
    detected_stances TEXT,
    verdict TEXT DEFAULT 'pending',
    comment TEXT,
    comment_lang TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (form_id) REFERENCES forms(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS general_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    lang TEXT NOT NULL,
    resolved INTEGER DEFAULT 0,
    resolution_note TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_takes_form ON reference_takes(form_id);
CREATE INDEX IF NOT EXISTS idx_tests_form ON tests(form_id);
CREATE INDEX IF NOT EXISTS idx_tests_created ON tests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON general_feedback(created_at DESC);
"""


@contextmanager
def conn():
    ensure_dirs()
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _migrate_schema() -> None:
    """Add columns to existing forms table if missing (SQLite ADD COLUMN)."""
    with conn() as c:
        existing = {row[1] for row in c.execute("PRAGMA table_info(forms)").fetchall()}
        for col_name, col_def in (
            ("weapon_category", "TEXT"),
            ("ai_guidelines", "TEXT"),
            ("expert_feedback", "TEXT"),
            ("expert_feedback_lang", "TEXT DEFAULT 'zh'"),
        ):
            if col_name not in existing:
                c.execute(f"ALTER TABLE forms ADD COLUMN {col_name} {col_def}")


def init_db() -> None:
    ensure_dirs()
    with conn() as c:
        c.executescript(SCHEMA)
    _migrate_schema()


def seed_forms_from_yaml() -> None:
    """
    Sync forms.yaml metadata into DB.
    - Inserts new forms, updates metadata of existing ones (preserves status, takes, tests).
    - Deletes orphan forms (in DB but not in YAML) IF they have no takes and no tests.
    """
    if not FORMS_YAML.exists():
        return
    data = yaml.safe_load(FORMS_YAML.read_text(encoding="utf-8")) or {}
    yaml_ids = {f["id"] for f in data.get("forms", [])}

    with conn() as c:
        # Delete orphans only if they have no children
        existing_ids = {r[0] for r in c.execute("SELECT id FROM forms").fetchall()}
        orphan_ids = existing_ids - yaml_ids
        for oid in orphan_ids:
            takes = c.execute(
                "SELECT COUNT(*) FROM reference_takes WHERE form_id=?", (oid,)
            ).fetchone()[0]
            tests = c.execute(
                "SELECT COUNT(*) FROM tests WHERE form_id=?", (oid,)
            ).fetchone()[0]
            if takes == 0 and tests == 0:
                c.execute("DELETE FROM forms WHERE id=?", (oid,))

        for f in data.get("forms", []):
            ai_guidelines_json = (
                json.dumps(f["intro"], ensure_ascii=False) if f.get("intro") else None
            )
            row = c.execute("SELECT id FROM forms WHERE id=?", (f["id"],)).fetchone()
            base_params = (
                f["dan_level"],
                f["name"]["ko"], f["name"]["zh"], f["name"].get("en"),
                f.get("duration_sec_estimate"),
                f.get("description", {}).get("ko"),
                f.get("description", {}).get("zh"),
                json.dumps(f.get("primary_stances", []), ensure_ascii=False),
                f.get("weapon_category"),
                ai_guidelines_json,
            )
            if row:
                c.execute(
                    """UPDATE forms SET
                        dan_level=?, name_ko=?, name_zh=?, name_en=?,
                        duration_sec_estimate=?, description_ko=?, description_zh=?,
                        primary_stances=?, weapon_category=?, ai_guidelines=?,
                        updated_at=datetime('now')
                       WHERE id=?""",
                    (*base_params, f["id"]),
                )
            else:
                c.execute(
                    """INSERT INTO forms
                        (id, dan_level, name_ko, name_zh, name_en,
                         duration_sec_estimate, description_ko, description_zh,
                         primary_stances, weapon_category, ai_guidelines, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (f["id"], *base_params, f.get("status", "draft")),
                )


# ---------- Forms ----------

def list_forms(dan_level: Optional[int] = None) -> list[dict]:
    with conn() as c:
        if dan_level is None:
            rows = c.execute(
                "SELECT * FROM forms ORDER BY dan_level, id"
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM forms WHERE dan_level=? ORDER BY id", (dan_level,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_form(form_id: str) -> Optional[dict]:
    with conn() as c:
        r = c.execute("SELECT * FROM forms WHERE id=?", (form_id,)).fetchone()
        return dict(r) if r else None


def upsert_form(payload: dict) -> None:
    with conn() as c:
        existing = c.execute("SELECT id FROM forms WHERE id=?", (payload["id"],)).fetchone()
        primary_stances = json.dumps(payload.get("primary_stances", []), ensure_ascii=False)
        if existing:
            c.execute(
                """UPDATE forms SET
                    dan_level=?, name_ko=?, name_zh=?, name_en=?,
                    duration_sec_estimate=?, description_ko=?, description_zh=?,
                    primary_stances=?, updated_at=datetime('now')
                   WHERE id=?""",
                (
                    payload["dan_level"], payload["name_ko"], payload["name_zh"],
                    payload.get("name_en"), payload.get("duration_sec_estimate"),
                    payload.get("description_ko"), payload.get("description_zh"),
                    primary_stances, payload["id"],
                ),
            )
        else:
            c.execute(
                """INSERT INTO forms
                    (id, dan_level, name_ko, name_zh, name_en,
                     duration_sec_estimate, description_ko, description_zh,
                     primary_stances, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')""",
                (
                    payload["id"], payload["dan_level"],
                    payload["name_ko"], payload["name_zh"], payload.get("name_en"),
                    payload.get("duration_sec_estimate"),
                    payload.get("description_ko"), payload.get("description_zh"),
                    primary_stances,
                ),
            )


def delete_form(form_id: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM forms WHERE id=?", (form_id,))


def update_form_status(form_id: str, status: str) -> None:
    with conn() as c:
        c.execute(
            "UPDATE forms SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, form_id),
        )


def update_form_feedback(form_id: str, feedback: str | None, lang: str) -> None:
    """Save expert's freeform feedback for a form (auto-translated for the other party)."""
    with conn() as c:
        c.execute(
            """UPDATE forms SET expert_feedback=?, expert_feedback_lang=?,
                                updated_at=datetime('now')
               WHERE id=?""",
            (feedback, lang, form_id),
        )


def get_form_guidelines(form_id: str) -> dict | None:
    """Return parsed ai_guidelines JSON or None."""
    form = get_form(form_id)
    if not form:
        return None
    raw = form.get("ai_guidelines")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None


# ---------- Reference takes ----------

def add_reference_take(
    form_id: str, video_path, pose_path, overlay_path,
    duration_sec: float, self_rating: Optional[int],
    notes: Optional[str], notes_lang: str,
) -> int:
    with conn() as c:
        max_take = c.execute(
            "SELECT COALESCE(MAX(take_number), 0) FROM reference_takes WHERE form_id=?",
            (form_id,),
        ).fetchone()[0]
        new_n = (max_take or 0) + 1
        cur = c.execute(
            """INSERT INTO reference_takes
                (form_id, take_number, video_path, pose_path, overlay_path,
                 duration_sec, self_rating, notes, notes_lang)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                form_id, new_n, str(video_path), str(pose_path),
                str(overlay_path) if overlay_path else None,
                duration_sec, self_rating, notes, notes_lang,
            ),
        )
        c.execute(
            """UPDATE forms
                 SET status = CASE WHEN status='draft' THEN 'recorded' ELSE status END,
                     updated_at = datetime('now')
                 WHERE id=?""",
            (form_id,),
        )
        return cur.lastrowid


def list_reference_takes(form_id: str) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM reference_takes WHERE form_id=? ORDER BY take_number",
            (form_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_reference_take(take_id: int) -> Optional[dict]:
    with conn() as c:
        r = c.execute("SELECT * FROM reference_takes WHERE id=?", (take_id,)).fetchone()
        return dict(r) if r else None


def delete_reference_take(take_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM reference_takes WHERE id=?", (take_id,))


# ---------- Tests ----------

def add_test(
    form_id: str, video_path, pose_path, overlay_path,
    intent: Optional[str], intent_lang: str, expected: str, tags: list,
    ai_score: float, ai_issues: list, detected_stances: list,
) -> int:
    with conn() as c:
        cur = c.execute(
            """INSERT INTO tests
                (form_id, video_path, pose_path, overlay_path,
                 intent, intent_lang, expected, tags,
                 ai_score, ai_issues, detected_stances, verdict)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (
                form_id, str(video_path), str(pose_path) if pose_path else None,
                str(overlay_path) if overlay_path else None,
                intent, intent_lang, expected,
                json.dumps(tags, ensure_ascii=False),
                ai_score,
                json.dumps(ai_issues, ensure_ascii=False),
                json.dumps(detected_stances, ensure_ascii=False),
            ),
        )
        return cur.lastrowid


def list_tests(form_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    with conn() as c:
        if form_id:
            rows = c.execute(
                "SELECT * FROM tests WHERE form_id=? ORDER BY created_at DESC LIMIT ?",
                (form_id, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM tests ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_test(test_id: int) -> Optional[dict]:
    with conn() as c:
        r = c.execute("SELECT * FROM tests WHERE id=?", (test_id,)).fetchone()
        return dict(r) if r else None


def update_test_verdict(
    test_id: int, verdict: str, comment: Optional[str], comment_lang: Optional[str]
) -> None:
    with conn() as c:
        c.execute(
            "UPDATE tests SET verdict=?, comment=?, comment_lang=? WHERE id=?",
            (verdict, comment, comment_lang, test_id),
        )


def update_test_scores(
    test_id: int, ai_score: float, ai_issues: list, detected_stances: list,
    pose_path=None, overlay_path=None,
) -> None:
    with conn() as c:
        if pose_path is not None and overlay_path is not None:
            c.execute(
                """UPDATE tests SET ai_score=?, ai_issues=?, detected_stances=?,
                                    pose_path=?, overlay_path=? WHERE id=?""",
                (
                    ai_score,
                    json.dumps(ai_issues, ensure_ascii=False),
                    json.dumps(detected_stances, ensure_ascii=False),
                    str(pose_path), str(overlay_path), test_id,
                ),
            )
        else:
            c.execute(
                """UPDATE tests SET ai_score=?, ai_issues=?, detected_stances=? WHERE id=?""",
                (
                    ai_score,
                    json.dumps(ai_issues, ensure_ascii=False),
                    json.dumps(detected_stances, ensure_ascii=False),
                    test_id,
                ),
            )


def delete_test(test_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM tests WHERE id=?", (test_id,))


# ---------- Stats ----------

def stats() -> dict:
    with conn() as c:
        return {
            "forms_total": c.execute("SELECT COUNT(*) FROM forms").fetchone()[0],
            "forms_ready": c.execute("SELECT COUNT(*) FROM forms WHERE status='ready'").fetchone()[0],
            "references_total": c.execute("SELECT COUNT(*) FROM reference_takes").fetchone()[0],
            "tests_total": c.execute("SELECT COUNT(*) FROM tests").fetchone()[0],
        }


# ---------- General feedback (free-form, on Home page) ----------

def add_general_feedback(text: str, lang: str) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO general_feedback (text, lang) VALUES (?, ?)",
            (text, lang),
        )
        return cur.lastrowid


def list_general_feedback(limit: int = 30) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM general_feedback ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_general_feedback_resolution(
    feedback_id: int, resolved: bool, note: str | None = None
) -> None:
    with conn() as c:
        c.execute(
            "UPDATE general_feedback SET resolved=?, resolution_note=? WHERE id=?",
            (1 if resolved else 0, note, feedback_id),
        )


def delete_general_feedback(feedback_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM general_feedback WHERE id=?", (feedback_id,))


def recent_activity(limit: int = 10) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            """SELECT 'reference' AS kind, form_id, created_at,
                      id AS row_id, take_number AS detail
                 FROM reference_takes
               UNION ALL
               SELECT 'test' AS kind, form_id, created_at,
                      id AS row_id, NULL AS detail
                 FROM tests
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
