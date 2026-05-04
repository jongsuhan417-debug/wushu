-- Wushu Workbench — Supabase Postgres schema
-- Run this once in: Supabase Dashboard → SQL Editor → New query → Run
-- Idempotent: safe to re-run.

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
