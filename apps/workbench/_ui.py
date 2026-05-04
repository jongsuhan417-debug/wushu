"""Shared UI helpers — bootstrap, custom CSS, hero header, status pills, ..."""
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import streamlit as st


# Korea Standard Time (UTC+9, no DST). All timestamps from Postgres come back
# as TIMESTAMPTZ in UTC; convert here so the UI shows local Seoul time.
KST = timezone(timedelta(hours=9))


def bootstrap() -> None:
    """Set sys.path so pages can import core.*; bridge st.secrets to env vars
    so cloud deploys work without rewriting every os.environ.get call."""
    here = Path(__file__).resolve().parent
    project_root = here.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))

    # Streamlit Cloud delivers config via st.secrets (not env vars). Mirror it
    # into os.environ so code paths that read env vars keep working unchanged.
    # Walks nested TOML sections too — if someone wraps the secrets in a
    # [section] header, we still find the keys inside.
    import os
    try:
        import streamlit as st

        def _flatten(node):
            try:
                items = node.items()
            except AttributeError:
                return
            for k, v in items:
                if isinstance(v, (str, int, float, bool)):
                    os.environ[k] = str(v)
                else:
                    _flatten(v)

        _flatten(st.secrets)
        if not os.environ.get("STORAGE_BACKEND"):
            print(
                "[bootstrap] STORAGE_BACKEND not found in secrets — "
                "videos will resolve against the local filesystem.",
                flush=True,
            )
    except Exception as e:
        print(f"[bootstrap] secrets bridge skipped: {e!r}", flush=True)

    # Drop any singletons captured during a previous script run BEFORE the
    # bridge had a chance to populate the env. Streamlit reruns the script
    # on every user action but keeps module state, so a stale LocalStorage
    # cached on the very first run would otherwise stick forever — even
    # after secrets are correctly configured. Reset and let the next caller
    # rebuild from current env.
    try:
        from core import storage as _storage_mod
        _storage_mod._STORAGE = None
    except Exception:
        pass


bootstrap()

from core.db import init_db, seed_forms_from_yaml  # noqa: E402
from core.i18n import current_lang, t  # noqa: E402


def ensure_db_seeded() -> None:
    if st.session_state.get("_db_ready"):
        return
    import os
    if not os.environ.get("SUPABASE_DB_URL"):
        st.error(
            "⚠️ **SUPABASE_DB_URL secret이 설정되지 않았습니다.**\n\n"
            "Streamlit Cloud → 앱 우측 하단 **Manage app → Settings → Secrets** 에서 "
            "`SUPABASE_DB_URL`을 포함한 비밀 값을 입력 후 앱을 **Reboot** 하세요.\n\n"
            "예시는 `.streamlit/secrets.toml.example` 참고."
        )
        st.stop()
    init_db()
    seed_forms_from_yaml()
    st.session_state["_db_ready"] = True


CUSTOM_CSS = """
<style>
  /* === Design tokens ===
     Color:     primary #C0392B  primary-dark #8E2A20  accent #D4A574
                bg #FAF6EE  surface #FFFFFF  border #E8DFCD
                text #1F1B16  text-soft #6B635A  text-muted #9C9489
     Radius:    sm 8  md 12  lg 16  pill 999
     Shadow:    sm  0 1px 3px rgba(31,27,22,.04)
                md  0 4px 12px rgba(31,27,22,.08)
                lg  0 12px 32px rgba(31,27,22,.12)
     Spacing:   4 8 12 16 24 32 48
  */

  /* Hide default Streamlit chrome */
  #MainMenu, footer { visibility: hidden; }
  header[data-testid="stHeader"] { background: transparent; height: 0; }

  /* Body / typography */
  html, body, [class*="css"], .main {
    font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI",
                 "Noto Sans KR", "Noto Sans SC", "PingFang SC",
                 "Microsoft YaHei", sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: #1F1B16;
  }
  .stApp { background: #F4EEDF; }

  h1, h2, h3, h4, h5 {
    color: #1F1B16;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  h1 { font-size: 30px; line-height: 1.2; }
  h2 { font-size: 22px; line-height: 1.3; }
  h3 { font-size: 17px; line-height: 1.35; }
  h4 { font-size: 15px; line-height: 1.4; }
  p, li { color: #4A413A; line-height: 1.65; }
  [data-testid="stMarkdownContainer"] p { font-size: 14.5px; }
  [data-testid="stMarkdownContainer"] strong { color: #1F1B16; font-weight: 700; }
  [data-testid="stMarkdownContainer"] small { color: #7A726A; }

  /* Constrain content width — comfortable reading */
  .main .block-container {
    max-width: 980px;
    padding: 24px 24px 48px;
  }

  /* === Hero (page title) ===
     Bigger, more impactful — gradient accent bar
  */
  .wushu-hero {
    margin: 8px 0 28px;
    padding: 0 0 0 18px;
    position: relative;
  }
  .wushu-hero::before {
    content: '';
    position: absolute;
    left: 0; top: 6px; bottom: 6px;
    width: 5px;
    border-radius: 999px;
    background: linear-gradient(180deg, #C0392B 0%, #D4A574 100%);
  }
  .wushu-hero .eyebrow {
    color: #C0392B;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    margin-bottom: 6px;
  }
  .wushu-hero h1 {
    color: #1F1B16 !important;
    font-size: 28px;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.025em;
    line-height: 1.15;
  }
  .wushu-hero p {
    color: #6B635A;
    font-size: 15px;
    margin: 8px 0 0 0;
    font-weight: 400;
    line-height: 1.5;
  }

  /* === Primary CTA card — featured action ===
     Used on Home empty state
  */
  .wushu-cta {
    background: linear-gradient(135deg, #FFFFFF 0%, #FFF8EE 100%);
    border: 1px solid #E8DFCD;
    border-radius: 16px;
    padding: 32px 36px;
    margin: 20px 0 24px;
    box-shadow: 0 4px 12px rgba(31, 27, 22, 0.06);
    position: relative;
    overflow: hidden;
  }
  .wushu-cta::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 4px;
    background: linear-gradient(90deg, #C0392B 0%, #D4A574 100%);
  }
  .wushu-cta .cta-icon {
    font-size: 32px;
    margin-bottom: 8px;
  }
  .wushu-cta h2 {
    color: #1F1B16;
    margin: 0 0 8px 0;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .wushu-cta p {
    color: #6B635A;
    margin: 0 0 20px 0;
    font-size: 15px;
    line-height: 1.6;
  }

  /* === Notice / banner === */
  .wushu-notice {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #FFF6E5;
    border: 1px solid #F5D78E;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 20px;
    font-size: 13px;
    color: #6B5022;
  }
  .wushu-notice b { color: #8B6018; }

  /* === Pills (status / severity) === */
  .pill {
    display: inline-block;
    padding: 4px 11px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    line-height: 1.5;
    box-shadow: inset 0 -1px 0 rgba(0, 0, 0, 0.10);
  }
  .pill-ready    { background: linear-gradient(180deg, #2EA361 0%, #1F8A4C 100%); color: white; }
  .pill-recorded { background: linear-gradient(180deg, #DA8B27 0%, #C97A1B 100%); color: white; }
  .pill-draft    { background: linear-gradient(180deg, #A8A095 0%, #8C8579 100%); color: white; }
  .pill-ok    { background: linear-gradient(180deg, #2EA361 0%, #1F8A4C 100%); color: white; }
  .pill-warn  { background: linear-gradient(180deg, #DA8B27 0%, #C97A1B 100%); color: white; }
  .pill-bad   { background: linear-gradient(180deg, #C84938 0%, #B0392B 100%); color: white; }
  .pill-info  { background: linear-gradient(180deg, #3D6BB8 0%, #2D5BAD 100%); color: white; }
  .pill-pending { background: linear-gradient(180deg, #A8A095 0%, #8C8579 100%); color: white; }

  /* === Streamlit native st.metric polish === */
  [data-testid="stMetric"] {
    background: white;
    border: 1px solid #D9CFC2;
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 2px 6px rgba(31, 27, 22, 0.06);
    position: relative;
    overflow: hidden;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  [data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(31, 27, 22, 0.08);
  }
  [data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: linear-gradient(180deg, #C0392B 0%, #8E2A20 100%);
  }
  [data-testid="stMetricLabel"] {
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #9C9489 !important;
    font-weight: 700 !important;
  }
  [data-testid="stMetricValue"] {
    color: #1F1B16 !important;
    font-weight: 800 !important;
    font-size: 32px !important;
    letter-spacing: -0.025em !important;
  }

  /* === Containers (st.container border) ===
     Stronger border + shadow + breathing room for clear separation
  */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #D9CFC2 !important;
    background: #FFFFFF !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 6px rgba(31, 27, 22, 0.06) !important;
    padding: 20px !important;
    margin-bottom: 12px !important;
  }

  /* === Custom metric/step/etc cards === */
  .metric-card {
    background: white;
    border: 1px solid #D9CFC2;
    border-radius: 14px;
    padding: 18px 22px;
    box-shadow: 0 2px 6px rgba(31, 27, 22, 0.06);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    position: relative;
    overflow: hidden;
  }
  .metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, #C0392B 0%, #8E2A20 100%);
  }
  .metric-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(31, 27, 22, 0.08); }
  .metric-card .label {
    font-size: 11px;
    color: #9C9489;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    font-weight: 700;
  }
  .metric-card .value {
    font-size: 32px;
    color: #1F1B16;
    font-weight: 800;
    margin-top: 4px;
    line-height: 1.1;
    letter-spacing: -0.025em;
  }
  .metric-card .sub {
    font-size: 12px;
    color: #9C9489;
    margin-top: 4px;
  }

  .step {
    display: flex;
    gap: 14px;
    align-items: center;
    background: white;
    border: 1px solid #D9CFC2;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: border-color 0.15s ease;
    box-shadow: 0 2px 6px rgba(31, 27, 22, 0.05);
  }
  .step:hover { border-color: #D4A574; }
  .step-num {
    background: linear-gradient(135deg, #C0392B 0%, #8E2A20 100%);
    color: white;
    border-radius: 50%;
    width: 30px; height: 30px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800;
    font-size: 13px;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(192, 57, 43, 0.25);
  }

  /* === Buttons — refined design system ===
     Primary: deep red gradient with soft glow
     Secondary: white card with crisp hover
     Icon-only (small): minimal borderless touch target
  */
  div[data-testid="stButton"] button,
  div[data-testid="stFormSubmitButton"] button {
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 0.005em !important;
    border-radius: 10px !important;
    padding: 10px 18px !important;
    transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
    line-height: 1.4 !important;
    min-height: 42px !important;
  }

  /* Primary — clean filled, refined wine red, compact height */
  div[data-testid="stButton"] button[kind="primary"],
  div[data-testid="stFormSubmitButton"] button {
    background: #A03128 !important;
    border: none !important;
    color: #FFFFFF !important;
    box-shadow: 0 1px 2px rgba(160, 49, 40, 0.20) !important;
    padding: 9px 18px !important;
    min-height: 40px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    text-shadow: none !important;
  }
  /* Force white on every nested text element (Streamlit wraps label in <p>) */
  div[data-testid="stButton"] button[kind="primary"] *,
  div[data-testid="stFormSubmitButton"] button * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
  }
  div[data-testid="stButton"] button[kind="primary"]:hover,
  div[data-testid="stFormSubmitButton"] button:hover {
    background: #872318 !important;
    box-shadow: 0 4px 12px rgba(160, 49, 40, 0.30) !important;
    transform: translateY(-1px) !important;
  }
  div[data-testid="stButton"] button[kind="primary"]:active,
  div[data-testid="stFormSubmitButton"] button:active {
    transform: translateY(0) !important;
    background: #6F1C12 !important;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.12) !important;
  }
  div[data-testid="stButton"] button[kind="primary"]:disabled,
  div[data-testid="stFormSubmitButton"] button:disabled {
    background: #E5DCD0 !important;
    color: #9C9489 !important;
    box-shadow: none !important;
    transform: none !important;
    cursor: not-allowed !important;
  }

  /* Secondary */
  div[data-testid="stButton"] button[kind="secondary"] {
    background: white !important;
    border: 1px solid #D9CFC2 !important;
    color: #1F1B16 !important;
    box-shadow: 0 1px 2px rgba(31, 27, 22, 0.04) !important;
  }
  div[data-testid="stButton"] button[kind="secondary"]:hover {
    background: #FFFAF0 !important;
    border-color: #C0392B !important;
    color: #C0392B !important;
    box-shadow: 0 2px 6px rgba(192, 57, 43, 0.10) !important;
    transform: translateY(-1px) !important;
  }
  div[data-testid="stButton"] button[kind="secondary"]:active {
    transform: translateY(0) !important;
  }
  div[data-testid="stButton"] button[kind="secondary"]:disabled {
    background: #F4EEDF !important;
    border-color: #E8DFCD !important;
    color: #B5A99A !important;
    cursor: not-allowed !important;
    transform: none !important;
  }

  /* Focus ring (accessibility) */
  div[data-testid="stButton"] button:focus-visible,
  div[data-testid="stFormSubmitButton"] button:focus-visible {
    outline: 2px solid rgba(192, 57, 43, 0.55) !important;
    outline-offset: 2px !important;
  }

  /* === Form controls === */
  [data-testid="stTextInput"] input,
  [data-testid="stTextArea"] textarea,
  [data-testid="stNumberInput"] input,
  [data-testid="stSelectbox"] [data-baseweb="select"] > div {
    border: 1px solid #D9CFC2 !important;
    border-radius: 10px !important;
    background: white !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    color: #1F1B16 !important;
    font-size: 14px !important;
  }
  [data-testid="stTextInput"] input,
  [data-testid="stNumberInput"] input {
    padding: 10px 14px !important;
  }
  [data-testid="stTextArea"] textarea {
    padding: 12px 14px !important;
    line-height: 1.55 !important;
  }
  [data-testid="stTextInput"] input:focus,
  [data-testid="stTextArea"] textarea:focus,
  [data-testid="stNumberInput"] input:focus {
    border-color: #C0392B !important;
    box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.12) !important;
    outline: none !important;
  }
  [data-testid="stTextInput"] input::placeholder,
  [data-testid="stTextArea"] textarea::placeholder {
    color: #B5A99A !important;
  }
  /* Field labels (the small label above each input) */
  [data-testid="stWidgetLabel"] label,
  [data-testid="stWidgetLabel"] p,
  [data-testid="stTextInput"] label,
  [data-testid="stTextArea"] label,
  [data-testid="stNumberInput"] label,
  [data-testid="stSelectbox"] label,
  [data-testid="stSlider"] label,
  [data-testid="stRadio"] label,
  [data-testid="stFileUploader"] label {
    color: #1F1B16 !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: -0.005em !important;
    margin-bottom: 6px !important;
  }

  /* Radio buttons — clear visible state */
  [data-testid="stRadio"] [role="radiogroup"] {
    gap: 16px !important;
  }
  [data-testid="stRadio"] [role="radiogroup"] label {
    font-weight: 500 !important;
    font-size: 14px !important;
    color: #4A413A !important;
    cursor: pointer;
    padding: 4px 0 !important;
  }
  [data-testid="stRadio"] [role="radiogroup"] label > div:first-child {
    background: white !important;
    border: 1.5px solid #B5A99A !important;
  }
  /* Checked radio circle */
  [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) > div:first-child,
  [data-testid="stRadio"] [role="radiogroup"] label > div[data-checked="true"]:first-child {
    border-color: #B0392B !important;
    background: #B0392B !important;
  }
  [data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div,
  [data-testid="stRadio"] [role="radiogroup"] label > div[data-checked="true"]:first-child > div {
    background: white !important;
  }

  /* Slider */
  [data-testid="stSlider"] [role="slider"] {
    background: #C0392B !important;
    box-shadow: 0 2px 6px rgba(192, 57, 43, 0.30) !important;
  }
  [data-testid="stSlider"] [data-baseweb="slider"] > div > div {
    background: linear-gradient(90deg, #C0392B 0%, #D44434 100%) !important;
  }

  /* === File uploader === */
  [data-testid="stFileUploader"] section {
    background: linear-gradient(135deg, #FFFEFB 0%, #FFF6E5 100%);
    border: 2px dashed #D9CFC2;
    border-radius: 14px;
    padding: 28px 24px;
    transition: all 0.15s ease;
  }
  [data-testid="stFileUploader"] section:hover {
    border-color: #C0392B;
    background: linear-gradient(135deg, #FFFEFB 0%, #FFF0DA 100%);
  }
  [data-testid="stFileUploader"] button {
    border-radius: 8px !important;
  }

  /* === Tabs === */
  [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid #E8DFCD;
  }
  [data-baseweb="tab"] {
    font-weight: 600;
    color: #6B635A;
    padding: 10px 16px !important;
    border-radius: 8px 8px 0 0 !important;
  }
  [data-baseweb="tab"][aria-selected="true"] {
    color: #C0392B;
    background: rgba(192, 57, 43, 0.06);
  }

  /* === Page links — featured navigation buttons === */
  [data-testid="stPageLink"] a,
  a[data-testid="stPageLink-NavLink"] {
    border: 1px solid #D9CFC2 !important;
    border-radius: 10px !important;
    background: white !important;
    transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 1px 3px rgba(31, 27, 22, 0.05) !important;
    padding: 14px 18px !important;
    color: #1F1B16 !important;
    font-weight: 600 !important;
    font-size: 14.5px !important;
    min-height: 50px !important;
    display: flex !important;
    align-items: center !important;
  }
  [data-testid="stPageLink"] a:hover,
  a[data-testid="stPageLink-NavLink"]:hover {
    border-color: #C0392B !important;
    background: linear-gradient(135deg, white 0%, #FFFAF0 100%) !important;
    color: #C0392B !important;
    transform: translateY(-2px) !important;
    box-shadow:
      0 4px 8px rgba(192, 57, 43, 0.10),
      0 8px 16px rgba(192, 57, 43, 0.06) !important;
  }

  /* === Horizontal rule === */
  hr {
    border: 0 !important;
    border-top: 1px solid #E8DFCD !important;
    margin: 28px 0 !important;
  }

  /* === Captions === */
  [data-testid="stCaptionContainer"] {
    color: #7A726A !important;
    font-size: 13px !important;
    line-height: 1.55 !important;
  }

  /* === Expander === */
  [data-testid="stExpander"] {
    border: 1px solid #D9CFC2;
    border-radius: 12px;
    background: white;
    box-shadow: 0 2px 6px rgba(31, 27, 22, 0.05);
    margin-bottom: 12px;
  }
  [data-testid="stExpander"] summary {
    padding: 12px 16px !important;
    border-radius: 12px !important;
    transition: background 0.12s ease;
    color: #1F1B16 !important;
    font-weight: 600 !important;
  }
  [data-testid="stExpander"] summary:hover { background: #FAF6EE !important; }

  /* === Sidebar — keep light, subtle === */
  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #F4EEDF 100%);
    border-right: 1px solid #D9CFC2;
    box-shadow: 2px 0 12px rgba(31, 27, 22, 0.04);
  }
  section[data-testid="stSidebar"] hr {
    border-top: 1px solid #E8DFCD !important;
    margin: 16px 0 !important;
  }
  section[data-testid="stSidebar"] .brand {
    font-weight: 800;
    font-size: 20px;
    color: #1F1B16;
    padding: 8px 0 2px 0;
    letter-spacing: -0.02em;
  }
  section[data-testid="stSidebar"] .brand-sub {
    color: #7A726A;
    font-size: 12px;
    margin-bottom: 10px;
  }

  /* === Sidebar language toggle — minimal segmented look === */
  [data-testid="stSidebar"] [data-testid="stButton"] button {
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 7px 8px !important;
    min-height: 34px !important;
    border-radius: 8px !important;
    letter-spacing: 0 !important;
    text-shadow: none !important;
    transition: all 0.15s ease !important;
  }
  /* Active language */
  [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
    background: #1F1B16 !important;
    border: 1px solid #1F1B16 !important;
    color: #FFFFFF !important;
    box-shadow: none !important;
  }
  [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover {
    background: #1F1B16 !important;
    transform: none !important;
  }
  /* Inactive language */
  [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #D9CFC2 !important;
    color: #6B635A !important;
    box-shadow: none !important;
  }
  [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"]:hover {
    background: #F4EEDF !important;
    border-color: #B5A99A !important;
    color: #1F1B16 !important;
    transform: none !important;
  }
  /* Tighten gap between the two toggle buttons */
  [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
    gap: 6px !important;
  }

  /* Sidebar nav items */
  [data-testid="stSidebarNav"] a {
    font-size: 15px;
    font-weight: 500;
    color: #4A413A;
    padding: 11px 14px;
    border-radius: 10px;
    margin: 3px 6px;
    transition: all 0.15s ease;
  }
  [data-testid="stSidebarNav"] a:hover {
    background: rgba(192, 57, 43, 0.06);
    color: #1F1B16;
  }
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: linear-gradient(90deg, rgba(192, 57, 43, 0.12), rgba(192, 57, 43, 0.04));
    color: #C0392B !important;
    font-weight: 700;
    border-left: 3px solid #C0392B;
  }

  /* === Sidebar control buttons (single clean shape, no nested borders) ===
     Three possible test-ids depending on state and Streamlit version:
       - collapsedControl       : hamburger when sidebar is closed (top-left)
       - stSidebarCollapseButton: close ('×') when sidebar is open (inside sidebar)
       - headerNoPadding         : raw button often wrapped inside the above
     We make the OUTER container the visible "card" and force every nested
     element (button, span, div, svg-wrapper) to be transparent + borderless.
  */

  /* Outer container: the visible button card */
  [data-testid="collapsedControl"] {
    background: white !important;
    border: 1px solid #D9CFC2 !important;
    border-radius: 10px !important;
    padding: 6px !important;
    box-shadow: 0 2px 8px rgba(31, 27, 22, 0.10) !important;
    margin: 12px !important;
    width: auto !important;
    min-width: 40px !important;
    min-height: 40px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
  }
  [data-testid="collapsedControl"]:hover {
    background: #FFF6E5 !important;
    border-color: #C0392B !important;
    box-shadow: 0 4px 12px rgba(192, 57, 43, 0.18) !important;
  }

  /* Collapse button (sidebar open) — same look as hamburger for consistency */
  [data-testid="stSidebarCollapseButton"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    padding: 6px !important;
    box-shadow: none !important;
    min-width: 36px !important;
    min-height: 36px !important;
  }
  [data-testid="stSidebarCollapseButton"]:hover {
    background: #F4EEDF !important;
    border-color: #D9CFC2 !important;
  }

  /* ALL nested elements inside both controls — strip their own styling */
  [data-testid="collapsedControl"] *,
  [data-testid="stSidebarCollapseButton"] * {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
  }

  /* SVG icon inside both controls — colored red */
  [data-testid="collapsedControl"] svg,
  [data-testid="stSidebarCollapseButton"] svg {
    color: #C0392B !important;
    fill: #C0392B !important;
    width: 22px !important;
    height: 22px !important;
  }

  /* === MOBILE OPTIMIZATION (≤ 768px) === */
  @media (max-width: 768px) {
    .main .block-container {
      max-width: 100% !important;
      padding: 16px 14px 32px !important;
    }

    /* Stack column rows vertically in main content */
    section[data-testid="stMain"] [data-testid="stHorizontalBlock"] {
      flex-direction: column !important;
      gap: 10px !important;
    }
    section[data-testid="stMain"] [data-testid="column"] {
      width: 100% !important;
      flex: 1 1 auto !important;
      min-width: 0 !important;
    }

    /* Keep sidebar columns horizontal (e.g. language toggle) */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
      flex-direction: row !important;
      gap: 6px !important;
    }
    [data-testid="stSidebar"] [data-testid="column"] {
      width: auto !important;
      flex: 1 1 0 !important;
    }

    /* Touch-friendly buttons & links */
    [data-testid="stButton"] button,
    [data-testid="stPageLink"] a,
    [data-testid="stPageLink-NavLink"] a,
    [data-testid="stFormSubmitButton"] button {
      min-height: 48px !important;
      font-size: 15px !important;
    }

    html, body, p, li, label, [data-testid="stMarkdownContainer"] {
      font-size: 15px !important;
    }
    h1 { font-size: 24px !important; }
    h2 { font-size: 19px !important; }
    h3 { font-size: 16px !important; }

    /* Hero / CTA mobile */
    .wushu-hero { padding-left: 14px; margin-bottom: 18px; }
    .wushu-hero h1 { font-size: 22px !important; }
    .wushu-hero p { font-size: 13px !important; }
    .wushu-hero .eyebrow { font-size: 11px !important; }

    .wushu-cta { padding: 22px 20px !important; }
    .wushu-cta h2 { font-size: 19px !important; }
    .wushu-cta p { font-size: 14px !important; }

    div[data-testid="stVerticalBlockBorderWrapper"] { padding: 14px !important; }

    [data-testid="stMetric"] { padding: 14px 16px !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; }

    .metric-card { padding: 14px 16px !important; }
    .metric-card .value { font-size: 24px !important; }

    .step { padding: 12px 14px !important; font-size: 14px; }
    .step-num { width: 26px !important; height: 26px !important; font-size: 12px !important; }

    .pill { font-size: 10px !important; padding: 3px 9px !important; }

    /* Sidebar width on mobile */
    [data-testid="stSidebar"] {
      min-width: 280px !important;
      max-width: 84vw !important;
    }

    /* Hamburger button — bigger on mobile (single outer container) */
    [data-testid="collapsedControl"] {
      min-width: 48px !important;
      min-height: 48px !important;
      margin: 12px !important;
      box-shadow: 0 4px 12px rgba(192, 57, 43, 0.18) !important;
    }
    [data-testid="stSidebarCollapseButton"] {
      min-width: 44px !important;
      min-height: 44px !important;
    }
    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg {
      width: 26px !important;
      height: 26px !important;
    }

    [data-testid="stSidebarNav"] a {
      min-height: 50px !important;
      padding: 13px 14px !important;
      font-size: 16px !important;
    }

    /* File uploader compact */
    [data-testid="stFileUploader"] section { padding: 18px 16px !important; }
    [data-testid="stFileUploader"] button { min-height: 44px !important; }

    video, .stVideo { width: 100% !important; height: auto !important; }

    [data-testid="stSelectbox"] [data-baseweb="select"] { min-height: 46px !important; }
    [data-baseweb="popover"] li { min-height: 42px !important; font-size: 15px !important; }
    [data-testid="stSlider"] [role="slider"] { width: 22px !important; height: 22px !important; }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
      font-size: 15px !important;
      min-height: 46px !important;
    }
  }

  @media (max-width: 480px) {
    .main .block-container { padding: 12px 12px 24px !important; }
    .wushu-hero h1 { font-size: 20px !important; }
    .wushu-cta { padding: 18px 14px !important; }
    .wushu-cta h2 { font-size: 17px !important; }
    [data-testid="stMetricValue"] { font-size: 22px !important; }
  }
</style>
"""


def inject_css() -> None:
    # Inject every rerun so every page gets identical styling — Streamlit's
    # page-switch can lose previously injected style scope in some edge cases.
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str = "", eyebrow: str = "") -> None:
    """Page title — gradient accent bar + bold h1 + caption."""
    eyebrow_html = f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ''
    sub_html = f'<p>{subtitle}</p>' if subtitle else ''
    st.markdown(
        f'<div class="wushu-hero">{eyebrow_html}<h1>{title}</h1>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value, sub: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
          {f'<div class="sub">{sub}</div>' if sub else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(status: str) -> str:
    """Return HTML for a status pill given a form status code."""
    if status in ("draft", "recorded", "ready"):
        label = t("forms.status_" + status)
    else:
        label = status
    return f'<span class="pill pill-{status}">{label}</span>'


def severity_pill(sev: str, label: str = None) -> str:
    label = label or sev
    return f'<span class="pill pill-{sev}">{label}</span>'


def verdict_pill(verdict: str | None) -> str:
    if not verdict or verdict == "pending":
        return f'<span class="pill pill-pending">{t("test_lab.verdict_pending")}</span>'
    mapping = {
        "correct": ("ok", t("test_lab.verdict_correct")),
        "missed":  ("bad", t("test_lab.verdict_missed")),
        "wrong":   ("warn", t("test_lab.verdict_wrong")),
    }
    sev, lbl = mapping.get(verdict, ("pending", verdict))
    return f'<span class="pill pill-{sev}">{lbl}</span>'


def form_display_name(form: dict) -> str:
    lang = current_lang()
    return form["name_zh"] if lang == "zh" else form["name_ko"]


def fmt_dt(value) -> str:
    """Format DB timestamp as short Korea Standard Time string.

    Accepts both Postgres ``datetime`` (TIMESTAMPTZ → tz-aware) and legacy
    SQLite ISO strings (treated as UTC if naive).
    """
    if not value:
        return ""
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, AttributeError, TypeError):
            return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")
