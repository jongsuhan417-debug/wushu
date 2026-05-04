"""Reference Studio — expert uploads demonstration videos for a form."""
import shutil
import tempfile
import uuid
from pathlib import Path

import streamlit as st

from _ui import hero, status_pill, form_display_name, fmt_dt
from core.db import (
    list_forms, get_form, list_reference_takes, add_reference_take,
    delete_reference_take as db_delete_reference_take,
    get_reference_take, update_form_status, update_form_feedback,
    update_reference_take_overlay, get_form_guidelines,
)
from core.i18n import t, current_lang
from core.pose_extractor import extract_pose_sequence, save_pose_sequence, load_pose_sequence
from core.visualizer import render_overlay
from core.translator import translate
from core.storage import get_storage, video_key, pose_key, overlay_key


RECOMMENDED_TAKES = 3


def _save_uploaded_to_temp(file_bytes: bytes, ext: str) -> Path:
    """Write upload bytes to a temp file. Caller must clean up the parent dir."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="wushu-up-"))
    out = tmp_dir / f"upload{ext}"
    out.write_bytes(file_bytes)
    return out


def _cleanup_temp(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
        if path.parent.exists():
            shutil.rmtree(path.parent, ignore_errors=True)
    except OSError:
        pass


def _process_take(
    form_id: str, video_temp_path: Path, ext: str,
    self_rating: int, notes: str, notes_lang: str,
) -> None:
    storage = get_storage()
    uid = uuid.uuid4().hex
    vkey = video_key("references", form_id, uid, ext)
    pkey = pose_key("references", form_id, uid)
    okey = overlay_key("references", form_id, uid)

    with st.status(t("reference_studio.processing_extract"), expanded=True) as status:
        pb = st.progress(0.0)

        def cb(p: float) -> None:
            pb.progress(min(1.0, max(0.0, p)))

        pose_seq = extract_pose_sequence(video_temp_path, progress_callback=cb)
        pb.progress(1.0)

        # Render overlay + serialize pose to a temp dir, then upload all three
        with tempfile.TemporaryDirectory(prefix="wushu-out-") as tmpd:
            pose_tmp = Path(tmpd) / "pose.json"
            overlay_tmp = Path(tmpd) / "overlay.mp4"

            save_pose_sequence(pose_seq, pose_tmp)

            status.update(label=t("reference_studio.processing_render"))
            render_overlay(video_temp_path, pose_seq, overlay_tmp)

            status.update(label=t("reference_studio.processing_save"))
            storage.upload(video_temp_path, vkey)
            storage.upload(pose_tmp, pkey)
            storage.upload(overlay_tmp, okey)

        add_reference_take(
            form_id=form_id,
            video_path=vkey,
            pose_path=pkey,
            overlay_path=okey,
            duration_sec=pose_seq.get("duration_sec", 0.0),
            self_rating=self_rating,
            notes=notes,
            notes_lang=notes_lang,
        )

        status.update(label=t("reference_studio.saved_success"), state="complete")

    _cleanup_temp(video_temp_path)


def _render_guideline_panel(form: dict) -> None:
    """AI-generated guidelines from CWA Duan Wei official sources."""
    guidelines = get_form_guidelines(form["id"])
    if not guidelines:
        return

    lang = current_lang()
    source = guidelines.get("source", {})
    verified = guidelines.get("verified_facts", {}).get(lang, []) or \
        guidelines.get("verified_facts", {}).get("ko", [])
    pending = guidelines.get("pending", {}).get(lang, []) or \
        guidelines.get("pending", {}).get("ko", [])

    title = t("reference_studio.guidelines_title")
    src_label = t("reference_studio.guidelines_source")
    verified_label = t("reference_studio.guidelines_verified")
    pending_label = t("reference_studio.guidelines_pending")

    with st.expander(f"📋  {title}", expanded=False):
        st.caption(t("reference_studio.guidelines_help"))

        # Source citation block
        src_title = source.get("title", "")
        src_pub = source.get("publisher", "")
        src_isbn = source.get("isbn")
        src_url = source.get("url")
        src_year = source.get("year")
        src_meta = " · ".join(
            x for x in [
                src_title,
                src_pub,
                f"ISBN {src_isbn}" if src_isbn else None,
                str(src_year) if src_year else None,
            ] if x
        )
        st.markdown(
            f"""<div style='background:#FFFCF7;border:1px solid #ECE5DC;
                          border-radius:8px;padding:10px 12px;margin:8px 0;font-size:13px'>
                  <b>{src_label}</b><br/>
                  {src_meta}
                  {f'<br/><a href="{src_url}" target="_blank" style="font-size:12px">'
                   f'🔗 {t("reference_studio.guidelines_view_source")}</a>'
                   if src_url else ''}
                </div>""",
            unsafe_allow_html=True,
        )

        # Special note (e.g. for 24式 — not 段位制)
        note_key = "note_zh" if lang == "zh" else "note_ko"
        if source.get(note_key):
            st.info(source[note_key])

        # Verified facts
        if verified:
            st.markdown(f"**✅ {verified_label}**")
            for line in verified:
                st.markdown(
                    f"<div style='font-size:13px;margin:2px 0;padding-left:8px'>{line}</div>",
                    unsafe_allow_html=True,
                )

        # Pending items
        if pending:
            st.markdown("")
            st.markdown(f"**⚠️ {pending_label}**")
            for line in pending:
                st.markdown(
                    f"<div style='font-size:13px;margin:2px 0;padding-left:8px;color:#C97A1B'>"
                    f"• {line}</div>",
                    unsafe_allow_html=True,
                )


def _render_feedback_panel(form: dict) -> None:
    """Expert's freeform feedback textarea, per-form, with auto-translation display."""
    lang = current_lang()
    title = t("reference_studio.expert_feedback_title")

    existing = form.get("expert_feedback") or ""
    existing_lang = form.get("expert_feedback_lang") or "zh"

    with st.expander(f"✏️  {title}", expanded=bool(existing)):
        st.caption(t("reference_studio.expert_feedback_help"))

        feedback_lang = st.radio(
            t("reference_studio.expert_feedback_lang"),
            options=["zh", "ko"],
            index=0 if existing_lang == "zh" else 1,
            format_func=lambda x: {"zh": "中文", "ko": "한국어"}[x],
            horizontal=True,
            key=f"feedback_lang_{form['id']}",
        )
        new_feedback = st.text_area(
            " ",
            value=existing,
            placeholder=t("reference_studio.expert_feedback_placeholder"),
            height=120,
            key=f"feedback_{form['id']}",
            label_visibility="collapsed",
        )
        if st.button(
            t("reference_studio.expert_feedback_save"),
            type="primary",
            key=f"feedback_save_{form['id']}",
        ):
            cleaned = new_feedback.strip() or None
            update_form_feedback(form["id"], cleaned, feedback_lang)
            st.toast(t("reference_studio.expert_feedback_saved"), icon="✅")
            st.rerun()

        # Show translation if existing feedback is in different language than viewer
        if existing and existing_lang != lang:
            translated = translate(existing, lang, existing_lang)
            if translated and translated != existing:
                st.markdown(
                    f"""<div style='background:#EDF3FB;border-left:3px solid #2D5BAD;
                                  border-radius:6px;padding:10px 12px;margin-top:10px;font-size:13px'>
                          <small style='color:#6B635A'>
                          {t('translation.translated')} ({existing_lang} → {lang})
                          </small><br/>
                          {translated}
                        </div>""",
                    unsafe_allow_html=True,
                )


def _delete_take_with_files(take_id: int) -> None:
    """Delete take from DB + remove all backing files from storage."""
    take = get_reference_take(take_id)
    if take:
        storage = get_storage()
        for key_field in ("video_path", "pose_path", "overlay_path"):
            key = take.get(key_field)
            if key:
                storage.delete(key)
    db_delete_reference_take(take_id)


def _rerender_overlay(take: dict) -> None:
    """Re-render overlay video for an existing take using stored pose data.

    Writes to a NEW storage key so that mobile browsers cached on the previous
    URL fetch the fresh video instead of replaying the stale cached copy.
    The old overlay file is deleted afterward.
    """
    storage = get_storage()
    vkey = take.get("video_path")
    pkey = take.get("pose_path")
    old_okey = take.get("overlay_path")
    if not (vkey and pkey and storage.exists(vkey) and storage.exists(pkey)):
        raise FileNotFoundError("missing video or pose file")

    with storage.open_local(pkey) as local_pose:
        pose_seq = load_pose_sequence(local_pose)

    new_uid = uuid.uuid4().hex
    new_okey = overlay_key("references", take["form_id"], new_uid)

    with tempfile.TemporaryDirectory(prefix="wushu-rerender-") as tmpd:
        overlay_tmp = Path(tmpd) / "overlay.mp4"
        with storage.open_local(vkey) as local_video:
            render_overlay(local_video, pose_seq, overlay_tmp)
        storage.upload(overlay_tmp, new_okey)

    update_reference_take_overlay(take["id"], new_okey)
    if old_okey and old_okey != new_okey and storage.exists(old_okey):
        try:
            storage.delete(old_okey)
        except Exception:
            pass


def _render_take_card(take: dict) -> None:
    storage = get_storage()
    with st.container(border=True):
        cols = st.columns([2.5, 1])
        with cols[0]:
            st.markdown(
                f"**{t('reference_studio.take_label', n=take['take_number'])}**  ·  "
                f"<small style='color:#8C8579'>"
                f"{t('reference_studio.take_meta', rating=take['self_rating'] or '-', date=fmt_dt(take['created_at']))}"
                f"</small>",
                unsafe_allow_html=True,
            )
            overlay = take.get("overlay_path")
            video = take.get("video_path")
            if overlay and storage.exists(overlay):
                st.video(storage.url(overlay))
            elif video and storage.exists(video):
                st.video(storage.url(video))
            else:
                # Surface backend + key so we can tell apart "wrong backend",
                # "wrong credentials", and "missing object in R2".
                backend_name = getattr(storage, "backend_name", "?")
                missing = overlay or video or "(no path)"
                st.warning(
                    f"missing video file — backend=`{backend_name}` "
                    f"key=`{missing}`"
                )

            # Prominent re-render CTA right under the video (mobile-friendly)
            if st.button(
                f"🔄 {t('reference_studio.rerender_take')}",
                key=f"rerender_take_{take['id']}",
                type="primary",
                use_container_width=True,
                help=t("reference_studio.rerender_help"),
            ):
                try:
                    with st.spinner(t("reference_studio.rerendering")):
                        _rerender_overlay(take)
                    st.toast(t("reference_studio.rerendered"), icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"{t('common.error')}: {e}")

        with cols[1]:
            if take.get("notes"):
                st.markdown(
                    f"<div style='font-size:12px;color:#9C9489;font-weight:600;"
                    f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px'>"
                    f"{t('reference_studio.notes_label')}</div>"
                    f"<div style='background:#FFFAF0;border:1px solid #E8DFCD;"
                    f"border-radius:8px;padding:10px 12px;font-size:13px;color:#4A413A;"
                    f"line-height:1.5'>{take['notes']}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("")
            if st.button(
                t("reference_studio.delete_take"),
                key=f"del_take_{take['id']}",
                use_container_width=True,
            ):
                _delete_take_with_files(take["id"])
                st.toast(f"Take #{take['take_number']} deleted", icon="🗑")
                st.rerun()


def render() -> None:
    hero(
        title=t("reference_studio.title"),
        subtitle=t("reference_studio.subtitle"),
    )

    forms = list_forms()
    if not forms:
        st.info(t("forms.no_forms"))
        return

    # Form selector
    forms_by_id = {f["id"]: f for f in forms}
    form_options = {f["id"]: form_display_name(f) for f in forms}

    def _format_option(fid: str) -> str:
        dan = forms_by_id[fid]["dan_level"]
        return form_options[fid] + "  ·  " + t("forms.dan_" + str(dan))

    sel_id = st.selectbox(
        t("reference_studio.select_form"),
        options=list(form_options.keys()),
        format_func=_format_option,
        key="ref_form_select",
    )
    if not sel_id:
        st.info(t("reference_studio.no_form_selected"))
        return

    form = get_form(sel_id)

    # Form header strip — title + status inline
    head = st.columns([5, 2])
    head[0].markdown(
        f"<div style='font-size:18px;font-weight:700;margin-top:8px'>"
        f"{form_display_name(form)} &nbsp; {status_pill(form['status'])}</div>",
        unsafe_allow_html=True,
    )
    desc = form.get("description_zh") if current_lang() == "zh" else form.get("description_ko")
    if desc:
        st.markdown(
            f"<div style='color:#6B635A;font-size:13px;margin-bottom:18px'>{desc}</div>",
            unsafe_allow_html=True,
        )

    # AI guideline panel
    _render_guideline_panel(form)

    # Expert feedback panel
    _render_feedback_panel(form)

    st.markdown("---")

    # Existing takes
    takes = list_reference_takes(sel_id)
    st.markdown(f"#### {t('reference_studio.current_takes')}  ({len(takes)})")
    if not takes:
        st.info(t("reference_studio.no_takes"))
    else:
        for take in takes:
            _render_take_card(take)

    st.markdown("---")

    # Upload section
    st.markdown(f"#### {t('reference_studio.upload_new')}")
    with st.container(border=True):
        uploaded = st.file_uploader(
            t("reference_studio.upload_label"),
            type=["mp4", "mov", "m4v"],
            key=f"upload_{sel_id}",
        )
        cols = st.columns(2)
        self_rating = cols[0].slider(
            t("reference_studio.self_rating"),
            min_value=0, max_value=100, value=85, step=5,
            help=t("reference_studio.self_rating_help"),
        )
        notes_lang = cols[1].radio(
            t("translation.original"),
            options=["zh", "ko"],
            format_func=lambda x: {"zh": "中文", "ko": "한국어"}[x],
            horizontal=True,
            key=f"notes_lang_{sel_id}",
        )
        notes = st.text_area(
            t("reference_studio.notes_label"),
            placeholder=t("reference_studio.notes_placeholder"),
            height=80,
            key=f"notes_{sel_id}",
        )

        if st.button(
            t("reference_studio.process_btn"),
            type="primary",
            disabled=(uploaded is None),
            key=f"process_{sel_id}",
            use_container_width=True,
        ):
            ext = Path(uploaded.name).suffix.lower() or ".mp4"
            video_temp_path = _save_uploaded_to_temp(uploaded.getvalue(), ext)
            try:
                _process_take(
                    sel_id, video_temp_path, ext,
                    self_rating, notes.strip() or None, notes_lang,
                )
                st.toast(t("reference_studio.saved_success"), icon="✅")
                st.rerun()
            except Exception as e:
                _cleanup_temp(video_temp_path)
                st.error(f"{t('common.error')}: {e}")

    # Activate / deactivate button
    st.markdown("---")
    is_ready = form["status"] == "ready"
    can_activate = len(takes) >= 1 and not is_ready
    needed = max(0, RECOMMENDED_TAKES - len(takes))

    cols = st.columns([2, 1])
    with cols[0]:
        if is_ready:
            st.success(f"✅  {t('reference_studio.activated')}")
        elif needed > 0:
            st.markdown(
                f"<div style='color:#C97A1B'>"
                f"💡 {t('forms.needs_more_takes', needed=needed)}</div>",
                unsafe_allow_html=True,
            )
        st.caption(t("reference_studio.activate_help"))

    with cols[1]:
        if is_ready:
            # Deactivate path — drop status back to "recorded" (or "draft" if no takes)
            if st.button(
                f"⏸  {t('reference_studio.deactivate_form')}",
                type="secondary",
                use_container_width=True,
                key=f"deactivate_{sel_id}",
            ):
                next_status = "recorded" if len(takes) > 0 else "draft"
                update_form_status(sel_id, next_status)
                st.toast(t("reference_studio.deactivated"), icon="⏸")
                st.rerun()
        else:
            if st.button(
                f"✅  {t('reference_studio.activate_form')}",
                type="primary",
                disabled=not can_activate,
                use_container_width=True,
                key=f"activate_{sel_id}",
            ):
                update_form_status(sel_id, "ready")
                st.toast(t("reference_studio.activated"), icon="✅")
                st.rerun()
