"""Shared UI helpers — bootstrap, custom CSS, hero header, status pills, ..."""
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st


def bootstrap() -> None:
    """Set sys.path so pages can import core.* and ensure DB is initialized."""
    here = Path(__file__).resolve().parent
    project_root = here.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))


bootstrap()

from core.db import init_db, seed_forms_from_yaml  # noqa: E402
from core.i18n import current_lang, t  # noqa: E402


def ensure_db_seeded() -> None:
    if not st.session_state.get("_db_ready"):
        init_db()
        seed_forms_from_yaml()
        st.session_state["_db_ready"] = True


CUSTOM_CSS = """
<style>
  /* Hide default Streamlit chrome */
  #MainMenu, footer { visibility: hidden; }
  header[data-testid="stHeader"] { background: transparent; }

  /* Typography */
  html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard",
                 "Noto Sans KR", "Noto Sans SC", "PingFang SC", "Microsoft YaHei",
                 sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  h1, h2, h3, h4 { color: #1F1B16; letter-spacing: -0.01em; font-weight: 700; }
  h1 { font-size: 28px; }
  h2 { font-size: 22px; }
  h3 { font-size: 18px; }

  /* Page title — refined hero */
  .wushu-title {
    margin: 8px 0 24px;
    padding: 4px 0 4px 16px;
    border-left: 4px solid #C0392B;
    position: relative;
  }
  .wushu-title h1 {
    color: #1F1B16 !important;
    font-size: 26px;
    margin: 0;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.2;
  }
  .wushu-title p {
    color: #7A726A;
    margin: 6px 0 0 0;
    font-size: 14px;
    font-weight: 400;
  }

  /* Empty state CTA — elevated card */
  .wushu-cta {
    background: linear-gradient(135deg, #FFFFFF 0%, #FFFAF3 100%);
    border: 1px solid #ECE5DC;
    border-left: 4px solid #C0392B;
    border-radius: 14px;
    padding: 28px 32px;
    margin: 12px 0 20px;
    box-shadow: 0 4px 16px rgba(31, 27, 22, 0.05);
  }
  .wushu-cta h2 {
    color: #1F1B16;
    margin: 0 0 8px 0;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .wushu-cta p {
    color: #6B635A;
    margin: 0 0 16px 0;
    font-size: 14.5px;
    line-height: 1.55;
  }

  /* Status pills — refined with subtle inner shadow + gradient */
  .pill {
    display: inline-block;
    padding: 4px 11px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    box-shadow: inset 0 -1px 0 rgba(0, 0, 0, 0.10);
    line-height: 1.5;
  }
  .pill-ready    { background: linear-gradient(180deg, #2EA361 0%, #1F8A4C 100%); color: white; }
  .pill-recorded { background: linear-gradient(180deg, #DA8B27 0%, #C97A1B 100%); color: white; }
  .pill-draft    { background: linear-gradient(180deg, #9C9489 0%, #8C8579 100%); color: white; }
  .pill-ok    { background: linear-gradient(180deg, #2EA361 0%, #1F8A4C 100%); color: white; }
  .pill-warn  { background: linear-gradient(180deg, #DA8B27 0%, #C97A1B 100%); color: white; }
  .pill-bad   { background: linear-gradient(180deg, #C84938 0%, #B0392B 100%); color: white; }
  .pill-info  { background: linear-gradient(180deg, #3D6BB8 0%, #2D5BAD 100%); color: white; }
  .pill-pending { background: linear-gradient(180deg, #9C9489 0%, #8C8579 100%); color: white; }

  /* Metric cards — elevated with hover lift */
  .metric-card {
    background: white;
    border: 1px solid #ECE5DC;
    border-radius: 14px;
    padding: 18px 22px;
    box-shadow: 0 1px 3px rgba(31, 27, 22, 0.04);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    position: relative;
    overflow: hidden;
  }
  .metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 3px;
    height: 100%;
    background: linear-gradient(180deg, #C0392B 0%, #8E2A20 100%);
  }
  .metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(31, 27, 22, 0.08);
  }
  .metric-card .label {
    font-size: 11px;
    color: #8C8579;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    font-weight: 700;
  }
  .metric-card .value {
    font-size: 34px;
    color: #1F1B16;
    font-weight: 800;
    margin-top: 4px;
    line-height: 1.1;
    letter-spacing: -0.02em;
  }
  .metric-card .sub {
    font-size: 12px;
    color: #8C8579;
    margin-top: 4px;
  }

  /* Step cards */
  .step {
    display: flex;
    gap: 14px;
    align-items: center;
    background: white;
    border: 1px solid #ECE5DC;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 8px;
    transition: border-color 0.15s ease;
    box-shadow: 0 1px 2px rgba(31, 27, 22, 0.03);
  }
  .step:hover { border-color: #D9CFC2; }
  .step-num {
    background: linear-gradient(135deg, #C0392B 0%, #8E2A20 100%);
    color: white;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 13px;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(192, 57, 43, 0.25);
  }

  /* Sidebar — keep Streamlit default look. Just style our brand markup. */
  [data-testid="stSidebar"] .brand {
    font-weight: 700;
    font-size: 17px;
    color: #1F1B16;
    padding: 4px 0 0 0;
  }
  [data-testid="stSidebar"] .brand-sub {
    color: #6B635A;
    font-size: 12px;
    margin-bottom: 8px;
  }

  /* Hamburger / sidebar collapse button — make it easy to find */
  button[kind="headerNoPadding"],
  [data-testid="stSidebarCollapseButton"],
  [data-testid="collapsedControl"] {
    background: #C0392B !important;
    color: white !important;
    border-radius: 8px !important;
    padding: 6px !important;
    box-shadow: 0 2px 8px rgba(192, 57, 43, 0.3) !important;
  }
  button[kind="headerNoPadding"] svg,
  [data-testid="stSidebarCollapseButton"] svg,
  [data-testid="collapsedControl"] svg {
    color: white !important;
    fill: white !important;
    width: 22px !important;
    height: 22px !important;
  }

  /* Buttons — polished primary */
  div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(180deg, #CC4232 0%, #B03625 100%);
    border: 1px solid #8E2A20;
    color: white;
    font-weight: 600;
    box-shadow: 0 2px 6px rgba(192, 57, 43, 0.2),
                inset 0 1px 0 rgba(255, 255, 255, 0.15);
    transition: all 0.15s ease;
    letter-spacing: 0.01em;
  }
  div[data-testid="stButton"] button[kind="primary"]:hover {
    background: linear-gradient(180deg, #B0392B 0%, #952819 100%);
    box-shadow: 0 4px 10px rgba(192, 57, 43, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.15);
    transform: translateY(-1px);
  }
  div[data-testid="stButton"] button[kind="primary"]:active {
    transform: translateY(0);
  }
  /* Secondary buttons — refined */
  div[data-testid="stButton"] button[kind="secondary"] {
    background: white;
    border: 1px solid #D9CFC2;
    color: #4A413A;
    font-weight: 500;
    transition: all 0.15s ease;
  }
  div[data-testid="stButton"] button[kind="secondary"]:hover {
    background: #FAF6F0;
    border-color: #B5A99A;
  }

  /* Container with border (Streamlit native) — elevated */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #ECE5DC !important;
    background: #FFFFFF !important;
    border-radius: 14px !important;
    box-shadow: 0 1px 3px rgba(31, 27, 22, 0.04) !important;
  }

  /* File uploader — more inviting */
  [data-testid="stFileUploader"] section {
    background: linear-gradient(135deg, #FFFEFB 0%, #FFF8EC 100%);
    border: 2px dashed #D9CFC2;
    border-radius: 14px;
    padding: 24px;
    transition: border-color 0.15s ease, background 0.15s ease;
  }
  [data-testid="stFileUploader"] section:hover {
    border-color: #C0392B;
    background: linear-gradient(135deg, #FFFEFB 0%, #FFF4E0 100%);
  }

  /* Form controls — softer borders, focus on red */
  [data-testid="stSelectbox"] [data-baseweb="select"] > div,
  [data-testid="stTextInput"] input,
  [data-testid="stTextArea"] textarea,
  [data-testid="stNumberInput"] input {
    border-color: #ECE5DC !important;
    border-radius: 10px !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
  }
  [data-testid="stTextInput"] input:focus,
  [data-testid="stTextArea"] textarea:focus,
  [data-testid="stNumberInput"] input:focus {
    border-color: #C0392B !important;
    box-shadow: 0 0 0 3px rgba(192, 57, 43, 0.12) !important;
  }

  /* Streamlit native st.metric — make it feel like our cards */
  [data-testid="stMetric"] {
    background: white;
    border: 1px solid #ECE5DC;
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 1px 3px rgba(31, 27, 22, 0.04);
    position: relative;
    overflow: hidden;
  }
  [data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 3px;
    height: 100%;
    background: linear-gradient(180deg, #C0392B 0%, #8E2A20 100%);
  }
  [data-testid="stMetricLabel"] {
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: #8C8579 !important;
    font-weight: 700 !important;
  }
  [data-testid="stMetricValue"] {
    color: #1F1B16 !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
  }

  /* Tabs */
  [data-baseweb="tab-list"] { gap: 8px; border-bottom-color: #ECE5DC; }
  [data-baseweb="tab"] { font-weight: 600; color: #6B635A; }
  [data-baseweb="tab"][aria-selected="true"] { color: #C0392B; }

  /* Page links (used on Home for navigation buttons) */
  [data-testid="stPageLink"] a,
  a[data-testid="stPageLink-NavLink"] {
    border: 1px solid #ECE5DC;
    border-radius: 10px;
    background: white;
    transition: all 0.15s ease;
    box-shadow: 0 1px 2px rgba(31, 27, 22, 0.03);
  }
  [data-testid="stPageLink"] a:hover,
  a[data-testid="stPageLink-NavLink"]:hover {
    border-color: #C0392B;
    background: #FFFAF3;
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(31, 27, 22, 0.06);
  }

  /* Horizontal rule — softer */
  hr {
    border-color: #ECE5DC !important;
    margin: 1.8rem 0 !important;
  }

  /* Captions — slightly warmer */
  [data-testid="stCaptionContainer"] {
    color: #7A726A !important;
    font-size: 13px !important;
    line-height: 1.5 !important;
  }

  /* Expander header — more inviting */
  [data-testid="stExpander"] summary {
    border-radius: 10px !important;
    transition: background 0.12s ease;
  }
  [data-testid="stExpander"] summary:hover {
    background: #FAF6F0 !important;
  }
  [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    border-radius: 10px !important;
  }

  /* Constrain content width on large screens for readability */
  .main .block-container {
    max-width: 1100px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
  }

  /* === MOBILE OPTIMIZATION (≤ 768px) === */
  @media (max-width: 768px) {
    .main .block-container {
      max-width: 100% !important;
      padding: 0.75rem 0.6rem 1.2rem !important;
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

    /* Readable base typography */
    html, body, p, li, label, [data-testid="stMarkdownContainer"] {
      font-size: 15px !important;
    }
    h1 { font-size: 22px !important; }
    h2 { font-size: 18px !important; }
    h3 { font-size: 16px !important; }
    h4 { font-size: 15px !important; }

    /* Hero / CTA */
    .wushu-title { padding-left: 10px; margin-bottom: 14px; }
    .wushu-title h1 { font-size: 20px !important; }
    .wushu-title p { font-size: 13px !important; }

    .wushu-cta { padding: 18px 16px !important; }
    .wushu-cta h2 { font-size: 17px !important; margin-bottom: 4px !important; }
    .wushu-cta p { font-size: 13px !important; margin-bottom: 12px !important; }

    /* Cards (st.container border) more compact */
    div[data-testid="stVerticalBlockBorderWrapper"] {
      padding: 12px !important;
    }

    /* Metric cards */
    .metric-card { padding: 14px 16px !important; }
    .metric-card .label { font-size: 11px !important; }
    .metric-card .value { font-size: 24px !important; }

    /* Step cards */
    .step { padding: 12px 14px !important; font-size: 14px; }
    .step-num { width: 24px !important; height: 24px !important; font-size: 12px !important; }

    /* Pills */
    .pill { font-size: 10px !important; padding: 2px 8px !important; }

    /* Sidebar width on mobile */
    [data-testid="stSidebar"] {
      min-width: 260px !important;
      max-width: 80vw !important;
    }

    /* Hamburger button — bigger and more obvious on mobile */
    button[kind="headerNoPadding"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {
      min-width: 44px !important;
      min-height: 44px !important;
      margin: 6px !important;
    }
    button[kind="headerNoPadding"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="collapsedControl"] svg {
      width: 26px !important;
      height: 26px !important;
    }

    /* Guide page sections more compact */
    .guide-section { padding: 16px 18px !important; margin-bottom: 12px; }
    .guide-section h3 { font-size: 16px !important; }
    .guide-table { font-size: 13px; }
    .guide-table th, .guide-table td { padding: 8px !important; }
    .guide-step-num { width: 22px !important; height: 22px !important; font-size: 12px !important; }

    /* File uploader compact + still tappable */
    [data-testid="stFileUploader"] section {
      padding: 14px !important;
    }
    [data-testid="stFileUploader"] button {
      min-height: 44px !important;
    }

    /* Video player full width */
    video, .stVideo {
      width: 100% !important;
      height: auto !important;
    }

    /* Selectbox more tappable */
    [data-testid="stSelectbox"] [data-baseweb="select"] {
      min-height: 44px !important;
    }
    [data-baseweb="popover"] li { min-height: 40px !important; font-size: 15px !important; }

    /* Slider thumb bigger */
    [data-testid="stSlider"] [role="slider"] {
      width: 22px !important;
      height: 22px !important;
    }

    /* Text area & input bigger */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
      font-size: 15px !important;
      min-height: 44px !important;
    }
  }

  /* === SMALL PHONES (≤ 480px portrait) === */
  @media (max-width: 480px) {
    .main .block-container { padding: 0.6rem 0.5rem 1rem !important; }
    .wushu-title h1 { font-size: 18px !important; }
    .wushu-cta { padding: 14px 12px !important; }
    .wushu-cta h2 { font-size: 16px !important; }
    .metric-card .value { font-size: 22px !important; }
    h1 { font-size: 20px !important; }
    h2 { font-size: 17px !important; }
  }
</style>
"""


def inject_css() -> None:
    if not st.session_state.get("_css_injected"):
        st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
        st.session_state["_css_injected"] = True


def hero(title: str, subtitle: str = "", eyebrow: str = "") -> None:
    """Minimal page title — left red bar + h1 + small caption."""
    sub_html = f'<p>{subtitle}</p>' if subtitle else ''
    st.markdown(
        f'<div class="wushu-title"><h1>{title}</h1>{sub_html}</div>',
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


def fmt_dt(value: str) -> str:
    """Format DB timestamp into short locale-friendly string."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return value
