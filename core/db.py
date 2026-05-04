"""Postgres (Supabase) persistence for forms, reference takes, tests, feedback.

Connection
----------
Reads ``SUPABASE_DB_URL`` from environment (loaded by core.paths via dotenv).
Use the Supabase **Transaction Pooler** URL (port 6543) so short-lived
Streamlit sessions don't exhaust connection slots.

JSON columns (``primary_stances``, ``ai_guidelines``, ``ai_issues``,
``detected_stances``, ``tags``) are stored as JSONB and returned as native
Python ``dict``/``list`` — callers should NOT call ``json.loads`` on them.
"""
from __future__ import annotations

import os
import json
from contextlib import contextmanager
from typing import Optional

import yaml
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from .paths import FORMS_YAML


SCHEMA = """
CREATE TABLE IF NOT EXISTS forms (
    id                    TEXT PRIMARY KEY,
    dan_level             INT NOT NULL,
    name_ko               TEXT NOT NULL,
    name_zh               TEXT NOT NULL,
    name_en               TEXT,
    duration_sec_estimate INT,
    description_ko        TEXT,
    description_zh        TEXT,
    primary_stances       JSONB DEFAULT '[]'::jsonb,
    weapon_category       TEXT,
    ai_guidelines         JSONB,
    expert_feedback       TEXT,
    expert_feedback_lang  TEXT DEFAULT 'zh',
    status                TEXT DEFAULT 'draft',
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reference_takes (
    id              BIGSERIAL PRIMARY KEY,
    form_id         TEXT NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
    take_number     INT NOT NULL,
    video_path      TEXT NOT NULL,
    pose_path       TEXT NOT NULL,
    overlay_path    TEXT,
    duration_sec    REAL,
    self_rating     INT,
    notes           TEXT,
    notes_lang      TEXT DEFAULT 'zh',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tests (
    id                BIGSERIAL PRIMARY KEY,
    form_id           TEXT NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
    video_path        TEXT NOT NULL,
    pose_path         TEXT,
    overlay_path      TEXT,
    intent            TEXT,
    intent_lang       TEXT DEFAULT 'zh',
    expected          TEXT,
    tags              JSONB DEFAULT '[]'::jsonb,
    ai_score          REAL,
    ai_issues         JSONB DEFAULT '[]'::jsonb,
    detected_stances  JSONB DEFAULT '[]'::jsonb,
    verdict           TEXT DEFAULT 'pending',
    comment           TEXT,
    comment_lang      TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS general_feedback (
    id              BIGSERIAL PRIMARY KEY,
    text            TEXT NOT NULL,
    lang            TEXT NOT NULL,
    resolved        BOOLEAN DEFAULT FALSE,
    resolution_note TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_takes_form       ON reference_takes(form_id);
CREATE INDEX IF NOT EXISTS idx_tests_form       ON tests(form_id);
CREATE INDEX IF NOT EXISTS idx_tests_created    ON tests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON general_feedback(created_at DESC);
"""


# ---------- Connection pool (singleton, lazy init) ----------

_POOL: Optional[ConnectionPool] = None


def _dsn() -> str:
    dsn = os.environ.get("SUPABASE_DB_URL", "").strip()
    if not dsn:
        raise RuntimeError(
            "SUPABASE_DB_URL is not set. Add the Supabase Transaction Pooler "
            "URL (port 6543) to your .env file."
        )
    return dsn


def _get_pool() -> ConnectionPool:
    global _POOL
    if _POOL is None:
        _POOL = ConnectionPool(
            conninfo=_dsn(),
            min_size=1,
            max_size=5,
            timeout=10,
            # Transaction Pooler doesn't fully support prepared statements;
            # disabling avoids "prepared statement already exists" surprises.
            kwargs={"prepare_threshold": None, "autocommit": False},
            open=True,
        )
    return _POOL


@contextmanager
def conn():
    """Yield a connection with dict_row factory. Auto-commits on success."""
    pool = _get_pool()
    with pool.connection() as c:
        c.row_factory = dict_row
        yield c


# ---------- Schema bootstrap ----------

def init_db() -> None:
    """Create tables if missing. Safe to call on every app start."""
    with conn() as c:
        c.execute(SCHEMA)


def seed_forms_from_yaml() -> None:
    """Sync forms.yaml metadata into DB.

    Inserts new forms, updates metadata on existing ones (preserves status,
    takes, tests). Deletes orphan forms (in DB but not in YAML) only if they
    have no takes and no tests.
    """
    if not FORMS_YAML.exists():
        return
    data = yaml.safe_load(FORMS_YAML.read_text(encoding="utf-8")) or {}
    yaml_ids = {f["id"] for f in data.get("forms", [])}

    with conn() as c:
        existing_ids = {
            r["id"] for r in c.execute("SELECT id FROM forms").fetchall()
        }
        for oid in existing_ids - yaml_ids:
            takes = c.execute(
                "SELECT COUNT(*) AS n FROM reference_takes WHERE form_id=%s",
                (oid,),
            ).fetchone()["n"]
            tests = c.execute(
                "SELECT COUNT(*) AS n FROM tests WHERE form_id=%s", (oid,)
            ).fetchone()["n"]
            if takes == 0 and tests == 0:
                c.execute("DELETE FROM forms WHERE id=%s", (oid,))

        for f in data.get("forms", []):
            ai_guidelines = f.get("intro") or None
            base_params = (
                f["dan_level"],
                f["name"]["ko"], f["name"]["zh"], f["name"].get("en"),
                f.get("duration_sec_estimate"),
                f.get("description", {}).get("ko"),
                f.get("description", {}).get("zh"),
                Json(f.get("primary_stances", [])),
                f.get("weapon_category"),
                Json(ai_guidelines) if ai_guidelines else None,
            )
            row = c.execute(
                "SELECT id FROM forms WHERE id=%s", (f["id"],)
            ).fetchone()
            if row:
                c.execute(
                    """UPDATE forms SET
                        dan_level=%s, name_ko=%s, name_zh=%s, name_en=%s,
                        duration_sec_estimate=%s, description_ko=%s, description_zh=%s,
                        primary_stances=%s, weapon_category=%s, ai_guidelines=%s,
                        updated_at=NOW()
                       WHERE id=%s""",
                    (*base_params, f["id"]),
                )
            else:
                c.execute(
                    """INSERT INTO forms
                        (id, dan_level, name_ko, name_zh, name_en,
                         duration_sec_estimate, description_ko, description_zh,
                         primary_stances, weapon_category, ai_guidelines, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (f["id"], *base_params, f.get("status", "draft")),
                )


# ---------- Forms ----------

def list_forms(dan_level: Optional[int] = None) -> list[dict]:
    with conn() as c:
        if dan_level is None:
            return c.execute(
                "SELECT * FROM forms ORDER BY dan_level, id"
            ).fetchall()
        return c.execute(
            "SELECT * FROM forms WHERE dan_level=%s ORDER BY id", (dan_level,)
        ).fetchall()


def get_form(form_id: str) -> Optional[dict]:
    with conn() as c:
        return c.execute(
            "SELECT * FROM forms WHERE id=%s", (form_id,)
        ).fetchone()


def upsert_form(payload: dict) -> None:
    with conn() as c:
        existing = c.execute(
            "SELECT id FROM forms WHERE id=%s", (payload["id"],)
        ).fetchone()
        stances = Json(payload.get("primary_stances") or [])
        if existing:
            c.execute(
                """UPDATE forms SET
                    dan_level=%s, name_ko=%s, name_zh=%s, name_en=%s,
                    duration_sec_estimate=%s, description_ko=%s, description_zh=%s,
                    primary_stances=%s, updated_at=NOW()
                   WHERE id=%s""",
                (
                    payload["dan_level"], payload["name_ko"], payload["name_zh"],
                    payload.get("name_en"), payload.get("duration_sec_estimate"),
                    payload.get("description_ko"), payload.get("description_zh"),
                    stances, payload["id"],
                ),
            )
        else:
            c.execute(
                """INSERT INTO forms
                    (id, dan_level, name_ko, name_zh, name_en,
                     duration_sec_estimate, description_ko, description_zh,
                     primary_stances, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft')""",
                (
                    payload["id"], payload["dan_level"],
                    payload["name_ko"], payload["name_zh"], payload.get("name_en"),
                    payload.get("duration_sec_estimate"),
                    payload.get("description_ko"), payload.get("description_zh"),
                    stances,
                ),
            )


def delete_form(form_id: str) -> None:
    with conn() as c:
        c.execute("DELETE FROM forms WHERE id=%s", (form_id,))


def update_form_status(form_id: str, status: str) -> None:
    with conn() as c:
        c.execute(
            "UPDATE forms SET status=%s, updated_at=NOW() WHERE id=%s",
            (status, form_id),
        )


def update_form_feedback(
    form_id: str, feedback: Optional[str], lang: str
) -> None:
    with conn() as c:
        c.execute(
            """UPDATE forms SET expert_feedback=%s, expert_feedback_lang=%s,
                                updated_at=NOW()
               WHERE id=%s""",
            (feedback, lang, form_id),
        )


def get_form_guidelines(form_id: str) -> Optional[dict]:
    """Return the parsed ai_guidelines dict (already JSONB-decoded) or None."""
    form = get_form(form_id)
    if not form:
        return None
    return form.get("ai_guidelines") or None


# ---------- Reference takes ----------

def add_reference_take(
    form_id: str, video_path, pose_path, overlay_path,
    duration_sec: float, self_rating: Optional[int],
    notes: Optional[str], notes_lang: str,
) -> int:
    with conn() as c:
        max_take = c.execute(
            "SELECT COALESCE(MAX(take_number), 0) AS n "
            "FROM reference_takes WHERE form_id=%s",
            (form_id,),
        ).fetchone()["n"]
        new_n = (max_take or 0) + 1
        new_id = c.execute(
            """INSERT INTO reference_takes
                (form_id, take_number, video_path, pose_path, overlay_path,
                 duration_sec, self_rating, notes, notes_lang)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (
                form_id, new_n, str(video_path), str(pose_path),
                str(overlay_path) if overlay_path else None,
                duration_sec, self_rating, notes, notes_lang,
            ),
        ).fetchone()["id"]
        c.execute(
            """UPDATE forms
                 SET status = CASE WHEN status='draft' THEN 'recorded' ELSE status END,
                     updated_at = NOW()
               WHERE id=%s""",
            (form_id,),
        )
        return new_id


def list_reference_takes(form_id: str) -> list[dict]:
    with conn() as c:
        return c.execute(
            "SELECT * FROM reference_takes WHERE form_id=%s ORDER BY take_number",
            (form_id,),
        ).fetchall()


def get_reference_take(take_id: int) -> Optional[dict]:
    with conn() as c:
        return c.execute(
            "SELECT * FROM reference_takes WHERE id=%s", (take_id,)
        ).fetchone()


def delete_reference_take(take_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM reference_takes WHERE id=%s", (take_id,))


def update_reference_take_overlay(take_id: int, overlay_path: str) -> None:
    with conn() as c:
        c.execute(
            "UPDATE reference_takes SET overlay_path=%s WHERE id=%s",
            (overlay_path, take_id),
        )


# ---------- Tests ----------

def add_test(
    form_id: str, video_path, pose_path, overlay_path,
    intent: Optional[str], intent_lang: str, expected: str, tags: list,
    ai_score: float, ai_issues: list, detected_stances: list,
) -> int:
    with conn() as c:
        return c.execute(
            """INSERT INTO tests
                (form_id, video_path, pose_path, overlay_path,
                 intent, intent_lang, expected, tags,
                 ai_score, ai_issues, detected_stances, verdict)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
               RETURNING id""",
            (
                form_id, str(video_path),
                str(pose_path) if pose_path else None,
                str(overlay_path) if overlay_path else None,
                intent, intent_lang, expected,
                Json(tags or []),
                ai_score,
                Json(ai_issues or []),
                Json(detected_stances or []),
            ),
        ).fetchone()["id"]


def list_tests(
    form_id: Optional[str] = None, limit: int = 50
) -> list[dict]:
    with conn() as c:
        if form_id:
            return c.execute(
                "SELECT * FROM tests WHERE form_id=%s "
                "ORDER BY created_at DESC LIMIT %s",
                (form_id, limit),
            ).fetchall()
        return c.execute(
            "SELECT * FROM tests ORDER BY created_at DESC LIMIT %s", (limit,)
        ).fetchall()


def get_test(test_id: int) -> Optional[dict]:
    with conn() as c:
        return c.execute(
            "SELECT * FROM tests WHERE id=%s", (test_id,)
        ).fetchone()


def update_test_verdict(
    test_id: int, verdict: str,
    comment: Optional[str], comment_lang: Optional[str],
) -> None:
    with conn() as c:
        c.execute(
            "UPDATE tests SET verdict=%s, comment=%s, comment_lang=%s "
            "WHERE id=%s",
            (verdict, comment, comment_lang, test_id),
        )


def update_test_scores(
    test_id: int, ai_score: float, ai_issues: list, detected_stances: list,
    pose_path=None, overlay_path=None,
) -> None:
    with conn() as c:
        if pose_path is not None and overlay_path is not None:
            c.execute(
                """UPDATE tests SET ai_score=%s, ai_issues=%s, detected_stances=%s,
                                    pose_path=%s, overlay_path=%s WHERE id=%s""",
                (
                    ai_score, Json(ai_issues or []), Json(detected_stances or []),
                    str(pose_path), str(overlay_path), test_id,
                ),
            )
        else:
            c.execute(
                """UPDATE tests SET ai_score=%s, ai_issues=%s, detected_stances=%s
                   WHERE id=%s""",
                (
                    ai_score, Json(ai_issues or []), Json(detected_stances or []),
                    test_id,
                ),
            )


def delete_test(test_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM tests WHERE id=%s", (test_id,))


# ---------- Stats ----------

def stats() -> dict:
    with conn() as c:
        return {
            "forms_total": c.execute(
                "SELECT COUNT(*) AS n FROM forms"
            ).fetchone()["n"],
            "forms_ready": c.execute(
                "SELECT COUNT(*) AS n FROM forms WHERE status='ready'"
            ).fetchone()["n"],
            "references_total": c.execute(
                "SELECT COUNT(*) AS n FROM reference_takes"
            ).fetchone()["n"],
            "tests_total": c.execute(
                "SELECT COUNT(*) AS n FROM tests"
            ).fetchone()["n"],
        }


# ---------- General feedback ----------

def add_general_feedback(text: str, lang: str) -> int:
    with conn() as c:
        return c.execute(
            "INSERT INTO general_feedback (text, lang) VALUES (%s, %s) "
            "RETURNING id",
            (text, lang),
        ).fetchone()["id"]


def list_general_feedback(limit: int = 30) -> list[dict]:
    with conn() as c:
        return c.execute(
            "SELECT * FROM general_feedback ORDER BY created_at DESC LIMIT %s",
            (limit,),
        ).fetchall()


def update_general_feedback_resolution(
    feedback_id: int, resolved: bool, note: Optional[str] = None,
) -> None:
    with conn() as c:
        c.execute(
            "UPDATE general_feedback SET resolved=%s, resolution_note=%s "
            "WHERE id=%s",
            (resolved, note, feedback_id),
        )


def delete_general_feedback(feedback_id: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM general_feedback WHERE id=%s", (feedback_id,))


def recent_activity(limit: int = 10) -> list[dict]:
    with conn() as c:
        return c.execute(
            """SELECT 'reference' AS kind, form_id, created_at,
                      id AS row_id, take_number AS detail
                 FROM reference_takes
               UNION ALL
               SELECT 'test' AS kind, form_id, created_at,
                      id AS row_id, NULL AS detail
                 FROM tests
               ORDER BY created_at DESC
               LIMIT %s""",
            (limit,),
        ).fetchall()
