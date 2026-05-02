"""Forms Catalog — list, add, edit, delete Wushu forms."""
import streamlit as st

from _ui import hero, status_pill, form_display_name
from core.db import (
    list_forms, get_form, upsert_form, delete_form, list_reference_takes,
)
from core.i18n import t, current_lang


@st.dialog(" ")
def _edit_dialog(form: dict | None = None) -> None:
    is_new = form is None
    title = t("forms_catalog.add_title") if is_new else t("forms_catalog.edit_title")
    st.markdown(f"#### {title}")

    fid = st.text_input(
        t("forms_catalog.field_id"),
        value=form["id"] if form else "",
        disabled=not is_new,
    )
    cols = st.columns(2)
    dan = cols[0].selectbox(
        t("forms_catalog.field_dan"),
        options=[1, 2, 3],
        format_func=lambda d: t(f"forms.dan_{d}"),
        index=(form["dan_level"] - 1) if form else 0,
    )
    duration = cols[1].number_input(
        t("forms_catalog.field_duration"),
        min_value=10, max_value=600,
        value=form["duration_sec_estimate"] if form and form.get("duration_sec_estimate") else 60,
        step=5,
    )
    name_ko = st.text_input(t("forms_catalog.field_name_ko"), value=form["name_ko"] if form else "")
    name_zh = st.text_input(t("forms_catalog.field_name_zh"), value=form["name_zh"] if form else "")
    name_en = st.text_input(t("forms_catalog.field_name_en"), value=(form.get("name_en") or "") if form else "")
    desc_ko = st.text_area(
        t("forms_catalog.field_description_ko"),
        value=(form.get("description_ko") or "") if form else "",
        height=68,
    )
    desc_zh = st.text_area(
        t("forms_catalog.field_description_zh"),
        value=(form.get("description_zh") or "") if form else "",
        height=68,
    )

    save_col, cancel_col = st.columns([1, 1])
    if save_col.button(t("forms_catalog.save"), type="primary", use_container_width=True):
        if not fid or not name_ko or not name_zh:
            st.error(f"{t('common.required')}: ID, name_ko, name_zh")
            return
        upsert_form({
            "id": fid.strip(),
            "dan_level": dan,
            "name_ko": name_ko.strip(),
            "name_zh": name_zh.strip(),
            "name_en": name_en.strip() or None,
            "duration_sec_estimate": int(duration),
            "description_ko": desc_ko.strip() or None,
            "description_zh": desc_zh.strip() or None,
            "primary_stances": form.get("primary_stances") if form else [],
        })
        st.toast(t("forms_catalog.added") if is_new else t("forms_catalog.updated"), icon="✅")
        st.rerun()
    if cancel_col.button(t("forms_catalog.cancel"), use_container_width=True):
        st.rerun()


def render() -> None:
    hero(
        title=t("forms_catalog.title"),
        subtitle=t("forms_catalog.subtitle"),
        eyebrow="📋",
    )

    head = st.columns([3, 1])
    head[0].markdown(f"### {t('forms_catalog.list_title')}")
    if head[1].button(
        f"+ {t('forms.add_new')}",
        type="primary",
        use_container_width=True,
        key="add_form_btn",
    ):
        _edit_dialog(None)

    # Group by dan level
    forms = list_forms()
    if not forms:
        st.info(t("forms.no_forms"))
        return

    for dan in (1, 2, 3):
        dan_forms = [f for f in forms if f["dan_level"] == dan]
        if not dan_forms:
            continue
        st.markdown(f"#### {t(f'forms.dan_{dan}')}")
        for f in dan_forms:
            takes_count = len(list_reference_takes(f["id"]))
            with st.container(border=True):
                cols = st.columns([3, 1.2, 1, 1, 1])
                cols[0].markdown(
                    f"**{form_display_name(f)}**  ·  "
                    f"<small style='color:#8C8579'>{f['id']} · ⏱ {f['duration_sec_estimate']}s</small>",
                    unsafe_allow_html=True,
                )
                cols[1].markdown(status_pill(f["status"]), unsafe_allow_html=True)
                cols[2].markdown(f"<small>{t('forms.takes_count', count=takes_count)}</small>", unsafe_allow_html=True)
                if cols[3].button("✏️", key=f"edit_{f['id']}", use_container_width=True):
                    _edit_dialog(f)
                if cols[4].button("🗑", key=f"del_{f['id']}", use_container_width=True):
                    if st.session_state.get(f"confirm_del_{f['id']}"):
                        delete_form(f["id"])
                        st.toast(t("forms_catalog.deleted"), icon="🗑")
                        st.session_state[f"confirm_del_{f['id']}"] = False
                        st.rerun()
                    else:
                        st.session_state[f"confirm_del_{f['id']}"] = True
                        st.toast(t("common.confirm_delete"), icon="⚠️")
                desc = f.get("description_zh") if current_lang() == "zh" else f.get("description_ko")
                if desc:
                    st.markdown(
                        f"<small style='color:#6B635A'>{desc}</small>",
                        unsafe_allow_html=True,
                    )
