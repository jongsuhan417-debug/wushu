"""Home — minimal landing page. Single CTA when empty, compact metrics when data exists."""
import textwrap

import streamlit as st

from _ui import hero, form_display_name, fmt_dt
from core.db import (
    stats, recent_activity, get_form,
    add_general_feedback, list_general_feedback,
    update_general_feedback_resolution, delete_general_feedback,
)
from core.i18n import t, current_lang
from core.translator import translate


def _md(html: str) -> None:
    cleaned = textwrap.dedent(html).strip()
    cleaned = "\n".join(line for line in cleaned.split("\n") if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


def render() -> None:
    hero(
        title=t("app.brand"),
        subtitle=t("app.tagline"),
    )

    # Pending feedback badge (visible to developer when expert leaves new feedback)
    pending_count = sum(
        1 for fb in list_general_feedback(100) if not fb.get("resolved")
    )
    if pending_count > 0:
        _md(f"""
            <div style='background:linear-gradient(135deg,#C84938 0%,#A8311E 100%);
                        color:white;border-radius:12px;
                        padding:14px 18px;margin:0 0 24px 0;font-size:14px;font-weight:600;
                        box-shadow:0 4px 12px rgba(192,57,43,0.20)'>
            🔔 {t('home.feedback_pending_badge', count=pending_count)}
            <span style='font-weight:400;opacity:0.9;margin-left:8px'>
            ↓ {t('home.feedback_title')}
            </span>
            </div>
        """)

    s = stats()
    has_data = s["references_total"] > 0 or s["tests_total"] > 0

    if not has_data:
        # Empty state — featured CTA
        _md(f"""
            <div class="wushu-cta">
              <h2>{t('home.cta_first_title')}</h2>
              <p>{t('home.cta_first_body')}</p>
            </div>
        """)
        registered_pages = st.session_state.get("_pages", {})
        cols = st.columns([1, 1, 2])
        if "reference" in registered_pages:
            cols[0].page_link(
                registered_pages["reference"],
                label=t("home.cta_first_btn"),
                use_container_width=True,
            )
        if "guide" in registered_pages:
            cols[1].page_link(
                registered_pages["guide"],
                label=t("home.cta_guide_btn"),
                use_container_width=True,
            )

        # Dev-stage notice (full label + body, single source of truth on Home)
        _md(f"""
            <div class="wushu-notice" style='margin-top:32px'>
              <span><b>{t('app.dev_badge')}</b> &nbsp;·&nbsp; {t('app.dev_notice_short')}</span>
            </div>
        """)

        st.markdown(
            f"<div style='color:#9C9489;font-size:12px;margin-top:14px;text-align:center'>"
            f"💡 {t('home.hint_sidebar')}</div>",
            unsafe_allow_html=True,
        )
    else:
        # Has data — compact metrics
        cols = st.columns(3)
        cols[0].metric(t("home.references_total"), s["references_total"])
        cols[1].metric(t("home.tests_total"), s["tests_total"])
        cols[2].metric(
            t("home.forms_ready"),
            f"{s['forms_ready']} / {s['forms_total']}",
        )

        # Recent activity (only if any)
        activity = recent_activity(8)
        if activity:
            st.markdown("")
            st.markdown(f"### {t('home.recent_activity')}")
            for row in activity:
                form = get_form(row["form_id"]) or {}
                fname = form_display_name(form) if form else row["form_id"]
                kind_icon = "🎥" if row["kind"] == "reference" else "🧪"
                detail = (
                    f" · take #{row['detail']}"
                    if row["kind"] == "reference" and row["detail"] else ""
                )
                _md(f"""
                    <div style='display:flex;justify-content:space-between;
                                padding:10px 4px;border-bottom:1px solid #ECE5DC;font-size:14px'>
                    <span>{kind_icon} {fname}{detail}</span>
                    <span style='color:#8C8579'>{fmt_dt(row['created_at'])}</span>
                    </div>
                """)

    # ---------- General feedback section (ALWAYS visible) ----------
    st.markdown("---")
    _render_feedback_section()


def _render_feedback_section() -> None:
    """Free-form feedback input + history. Available on every Home visit."""
    lang = current_lang()
    history = list_general_feedback(20)
    pending_count = sum(1 for fb in history if not fb.get("resolved"))

    title_suffix = ""
    if pending_count > 0:
        badge = t("home.feedback_pending_badge", count=pending_count)
        title_suffix = (
            f" <span style='background:#B0392B;color:white;font-size:12px;"
            f"font-weight:600;padding:3px 9px;border-radius:999px;"
            f"margin-left:8px;vertical-align:middle'>{badge}</span>"
        )

    _md(f"### {t('home.feedback_title')}{title_suffix}")
    st.caption(t("home.feedback_help"))

    with st.container(border=True):
        feedback_lang = st.radio(
            t("home.feedback_lang"),
            options=["zh", "ko"],
            index=0 if lang == "zh" else 1,
            format_func=lambda x: {"zh": "中文", "ko": "한국어"}[x],
            horizontal=True,
            key="general_feedback_lang",
        )
        text = st.text_area(
            " ",
            placeholder=t("home.feedback_placeholder"),
            height=100,
            key="general_feedback_text",
            label_visibility="collapsed",
        )
        if st.button(
            t("home.feedback_submit"),
            type="primary",
            use_container_width=True,
            key="general_feedback_submit",
        ):
            cleaned = (text or "").strip()
            if cleaned:
                add_general_feedback(cleaned, feedback_lang)
                st.toast(t("home.feedback_saved"), icon="✅")
                # Clear the input and rerun
                st.session_state["general_feedback_text"] = ""
                st.rerun()

    # History — auto-expand when there are pending items
    if history:
        with st.expander(
            t("home.feedback_history", count=len(history)),
            expanded=(pending_count > 0),
        ):
            for fb in history:
                _render_feedback_item(fb, lang)
    else:
        st.markdown(
            f"<div style='color:#8C8579;font-size:13px;margin-top:10px'>"
            f"{t('home.feedback_no_history')}</div>",
            unsafe_allow_html=True,
        )


def _render_feedback_item(fb: dict, viewer_lang: str) -> None:
    is_resolved = bool(fb.get("resolved"))
    badge = t("home.feedback_resolved") if is_resolved else t("home.feedback_pending")
    badge_color = "#1F8A4C" if is_resolved else "#C97A1B"

    with st.container(border=True):
        head = st.columns([3, 1])
        head[0].markdown(
            f"<small style='color:#8C8579'>#{fb['id']} · "
            f"{fmt_dt(fb['created_at'])} · {fb['lang']}</small>",
            unsafe_allow_html=True,
        )
        head[1].markdown(
            f"<div style='text-align:right'>"
            f"<span style='color:{badge_color};font-weight:600;font-size:12px'>{badge}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Original
        st.markdown(
            f"<div style='font-size:14px;padding:6px 0;white-space:pre-wrap'>{fb['text']}</div>",
            unsafe_allow_html=True,
        )

        # Translation if needed
        if fb["lang"] != viewer_lang:
            translated = translate(fb["text"], viewer_lang, fb["lang"])
            if translated and translated != fb["text"]:
                _md(f"""
                    <div style='background:#EDF3FB;border-left:3px solid #2D5BAD;
                                border-radius:6px;padding:8px 10px;margin-top:6px;font-size:13px'>
                    <small style='color:#6B635A'>
                    {t('translation.translated')} ({fb['lang']} → {viewer_lang})
                    </small><br/>
                    {translated}
                    </div>
                """)

        # Actions
        cols = st.columns([1, 1])
        if is_resolved:
            if cols[0].button(
                t("home.feedback_mark_pending"),
                key=f"fb_unresolve_{fb['id']}",
                use_container_width=True,
            ):
                update_general_feedback_resolution(fb["id"], False)
                st.rerun()
        else:
            if cols[0].button(
                t("home.feedback_mark_resolved"),
                key=f"fb_resolve_{fb['id']}",
                use_container_width=True,
                type="primary",
            ):
                update_general_feedback_resolution(fb["id"], True)
                st.rerun()
        if cols[1].button(
            f"🗑 {t('home.feedback_delete')}",
            key=f"fb_delete_{fb['id']}",
            use_container_width=True,
        ):
            delete_general_feedback(fb["id"])
            st.rerun()
