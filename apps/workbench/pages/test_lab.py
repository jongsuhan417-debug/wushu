"""Test Lab — upload variation videos and verify AI scoring."""
import json
import shutil
import tempfile
import uuid
from pathlib import Path

import streamlit as st

from _ui import hero, form_display_name, fmt_dt, verdict_pill, severity_pill
from core.db import (
    list_forms, get_form, list_reference_takes, list_tests, get_test,
    add_test, update_test_verdict, update_test_scores,
    delete_test as db_delete_test,
)
from core.i18n import t, current_lang
from core.pose_extractor import extract_pose_sequence, save_pose_sequence, load_pose_sequence
from core.visualizer import render_overlay
from core.scorer import score_against_reference
from core.stance_detector import detect_stance_sequence, stance_label
from core.translator import translate
from core.storage import get_storage, video_key, pose_key, overlay_key


def _save_test_video_to_temp(file_bytes: bytes, ext: str) -> tuple[Path, str]:
    tmp_dir = Path(tempfile.mkdtemp(prefix="wushu-test-"))
    uid = uuid.uuid4().hex
    out = tmp_dir / f"upload{ext}"
    out.write_bytes(file_bytes)
    return out, uid


def _cleanup_temp(path: Path) -> None:
    try:
        if path.parent.exists():
            shutil.rmtree(path.parent, ignore_errors=True)
    except OSError:
        pass


def _canonical_reference(form_id: str) -> dict | None:
    """Return pose sequence of the canonical reference take (highest self_rating)."""
    takes = list_reference_takes(form_id)
    if not takes:
        return None
    rated = [t_ for t_ in takes if t_.get("self_rating") is not None]
    chosen = max(rated, key=lambda x: x["self_rating"]) if rated else takes[0]
    pose_key_str = chosen.get("pose_path")
    if not pose_key_str:
        return None
    storage = get_storage()
    if not storage.exists(pose_key_str):
        return None
    with storage.open_local(pose_key_str) as local_pose:
        return load_pose_sequence(local_pose)


def _run_scoring(
    form_id: str, video_temp_path: Path, uid: str, ext: str,
    intent, intent_lang, expected, tags,
) -> int:
    storage = get_storage()
    vkey = video_key("tests", form_id, uid, ext)
    pkey = pose_key("tests", form_id, uid)
    okey = overlay_key("tests", form_id, uid)

    with st.status(t("reference_studio.processing_extract"), expanded=True) as status:
        pb = st.progress(0.0)
        pose_seq = extract_pose_sequence(
            video_temp_path,
            progress_callback=lambda p: pb.progress(min(1.0, max(0.0, p))),
        )

        ref_seq = _canonical_reference(form_id)
        if ref_seq is None:
            status.update(label="No reference take found", state="error")
            raise RuntimeError("Cannot score without reference")

        status.update(label="Scoring against reference...")
        result = score_against_reference(pose_seq, ref_seq, lang=current_lang())

        with tempfile.TemporaryDirectory(prefix="wushu-test-out-") as tmpd:
            pose_tmp = Path(tmpd) / "pose.json"
            overlay_tmp = Path(tmpd) / "overlay.mp4"

            save_pose_sequence(pose_seq, pose_tmp)

            status.update(label=t("reference_studio.processing_render"))
            render_overlay(
                video_temp_path, pose_seq, overlay_tmp,
                frame_status_func=result["frame_status_func"],
            )

            stances = detect_stance_sequence(pose_seq)

            status.update(label=t("reference_studio.processing_save"))
            storage.upload(video_temp_path, vkey)
            storage.upload(pose_tmp, pkey)
            storage.upload(overlay_tmp, okey)

        test_id = add_test(
            form_id=form_id,
            video_path=vkey,
            pose_path=pkey,
            overlay_path=okey,
            intent=intent,
            intent_lang=intent_lang,
            expected=expected,
            tags=tags,
            ai_score=result["total_score"],
            ai_issues=result["issues"],
            detected_stances=stances,
        )

        status.update(label=t("reference_studio.saved_success"), state="complete")
        return test_id


def _rerun_scoring(test: dict) -> None:
    """Re-run scoring for an existing test (regression). Re-renders overlay."""
    storage = get_storage()
    pkey = test.get("pose_path")
    vkey = test.get("video_path")
    okey = test.get("overlay_path")
    if not pkey or not storage.exists(pkey):
        return

    with storage.open_local(pkey) as local_pose:
        pose_seq = load_pose_sequence(local_pose)

    ref_seq = _canonical_reference(test["form_id"])
    if ref_seq is None:
        return

    result = score_against_reference(pose_seq, ref_seq, lang=current_lang())

    if vkey and okey and storage.exists(vkey):
        with tempfile.TemporaryDirectory(prefix="wushu-rerun-") as tmpd:
            overlay_tmp = Path(tmpd) / "overlay.mp4"
            with storage.open_local(vkey) as local_video:
                render_overlay(
                    local_video, pose_seq, overlay_tmp,
                    frame_status_func=result["frame_status_func"],
                )
            storage.upload(overlay_tmp, okey)

    stances = detect_stance_sequence(pose_seq)
    update_test_scores(
        test_id=test["id"],
        ai_score=result["total_score"],
        ai_issues=result["issues"],
        detected_stances=stances,
    )


def _delete_test_with_files(test_id: int) -> None:
    test = get_test(test_id)
    if test:
        storage = get_storage()
        for key_field in ("video_path", "pose_path", "overlay_path"):
            key = test.get(key_field)
            if key:
                storage.delete(key)
    db_delete_test(test_id)


def _render_test_card(test: dict) -> None:
    lang = current_lang()
    with st.container(border=True):
        # Header row: meta + verdict
        head = st.columns([3, 1.4, 1.4])
        head[0].markdown(
            f"<small style='color:#8C8579'>#{test['id']} · {fmt_dt(test['created_at'])}</small>",
            unsafe_allow_html=True,
        )
        # Score badge
        score = test.get("ai_score") or 0
        score_color = "ok" if score >= 7 else ("warn" if score >= 5 else "bad")
        score_label = t("test_lab.ai_score") + ": " + f"{score:.1f}"
        head[1].markdown(
            f"<div style='text-align:right'>"
            f"{severity_pill(score_color, score_label)}"
            f"</div>",
            unsafe_allow_html=True,
        )
        head[2].markdown(
            f"<div style='text-align:right'>{verdict_pill(test.get('verdict'))}</div>",
            unsafe_allow_html=True,
        )

        # Intent + expected + tags
        if test.get("intent"):
            intent_text = test["intent"]
            target_lang = lang
            src_lang = test.get("intent_lang", "zh")
            translated = ""
            if src_lang != target_lang:
                translated = translate(intent_text, target_lang, src_lang)
            block = (
                f"<div style='background:#FFFCF7;border:1px solid #ECE5DC;border-radius:8px;"
                f"padding:10px;margin:8px 0;font-size:13px'>"
                f"<b>{t('test_lab.intent_label')}</b>  ·  <small>{src_lang}</small><br/>"
                f"{intent_text}"
            )
            if translated and translated != intent_text:
                block += (
                    f"<hr style='border:0;border-top:1px solid #ECE5DC;margin:6px 0'/>"
                    f"<small style='color:#8C8579'>{t('translation.translated')} → {target_lang}</small><br/>"
                    f"{translated}"
                )
            block += "</div>"
            st.markdown(block, unsafe_allow_html=True)

        meta_cols = st.columns(2)
        if test.get("expected"):
            exp_label = {
                "catch": t("test_lab.expected_catch"),
                "pass": t("test_lab.expected_pass"),
                "either": t("test_lab.expected_either"),
            }.get(test["expected"], test["expected"])
            meta_cols[0].markdown(f"**{t('test_lab.expected')}**: {exp_label}")
        try:
            tags_arr = json.loads(test.get("tags") or "[]")
        except (TypeError, json.JSONDecodeError):
            tags_arr = []
        if tags_arr:
            tags_html = " ".join(
                f"<span class='pill pill-info' style='margin-right:4px'>{tag}</span>"
                for tag in tags_arr
            )
            meta_cols[1].markdown(tags_html, unsafe_allow_html=True)

        # Two columns: video + analysis
        body = st.columns([1.3, 1])
        with body[0]:
            storage = get_storage()
            overlay = test.get("overlay_path")
            video = test.get("video_path")
            if overlay and storage.exists(overlay):
                st.video(storage.url(overlay))
            elif video and storage.exists(video):
                st.video(storage.url(video))

        with body[1]:
            # Issues
            try:
                issues = json.loads(test.get("ai_issues") or "[]")
            except (TypeError, json.JSONDecodeError):
                issues = []
            st.markdown(f"**{t('test_lab.detected_issues')}**")
            if not issues:
                st.markdown(
                    f"<div style='color:#1F8A4C;font-size:13px'>✓ {t('test_lab.no_issues')}</div>",
                    unsafe_allow_html=True,
                )
            else:
                for iss in issues:
                    st.markdown(
                        f"""
                        <div style='font-size:13px;margin-bottom:6px;
                                    padding:6px 10px;background:#FDF6F2;
                                    border-left:3px solid #B0392B;border-radius:4px'>
                          <b>{iss.get('time_sec', 0):.2f}s</b> · {iss.get('joint_label', iss.get('joint'))}
                          <br/><small style='color:#6B635A'>
                          {t('scoring.current')}: {iss.get('test_deg')}° ·
                          {t('scoring.ideal')}: {iss.get('ref_deg')}° ·
                          Δ {iss.get('delta_deg')}°
                          </small>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Detected stances
            try:
                stances = json.loads(test.get("detected_stances") or "[]")
            except (TypeError, json.JSONDecodeError):
                stances = []
            if stances:
                st.markdown(f"**{t('test_lab.detected_stances')}**")
                stance_chips = " ".join(
                    f"<span class='pill pill-info' style='margin-right:4px;font-size:11px'>"
                    f"{s.get('time_sec', 0):.1f}s · {stance_label(s['stance'], lang)}</span>"
                    for s in stances[:8]
                )
                st.markdown(stance_chips, unsafe_allow_html=True)

        # Verdict bar
        st.markdown("---")
        v_cols = st.columns([1, 1, 1, 1.5])
        if v_cols[0].button(
            f"✓ {t('test_lab.verdict_correct')}",
            key=f"verdict_correct_{test['id']}",
            use_container_width=True,
            type="primary" if test.get("verdict") == "correct" else "secondary",
        ):
            update_test_verdict(test["id"], "correct", test.get("comment"), test.get("comment_lang"))
            st.rerun()
        if v_cols[1].button(
            f"✗ {t('test_lab.verdict_missed')}",
            key=f"verdict_missed_{test['id']}",
            use_container_width=True,
            type="primary" if test.get("verdict") == "missed" else "secondary",
        ):
            update_test_verdict(test["id"], "missed", test.get("comment"), test.get("comment_lang"))
            st.rerun()
        if v_cols[2].button(
            f"✗ {t('test_lab.verdict_wrong')}",
            key=f"verdict_wrong_{test['id']}",
            use_container_width=True,
            type="primary" if test.get("verdict") == "wrong" else "secondary",
        ):
            update_test_verdict(test["id"], "wrong", test.get("comment"), test.get("comment_lang"))
            st.rerun()
        if v_cols[3].button(
            f"🗑 {t('test_lab.delete')}",
            key=f"del_{test['id']}",
            use_container_width=True,
        ):
            _delete_test_with_files(test["id"])
            st.toast("Test deleted", icon="🗑")
            st.rerun()

        # Comment
        with st.expander(t("test_lab.add_comment")):
            cur_comment = test.get("comment") or ""
            cur_lang = test.get("comment_lang") or current_lang()
            new_lang = st.radio(
                t("translation.original"),
                options=["zh", "ko"],
                index=0 if cur_lang == "zh" else 1,
                format_func=lambda x: {"zh": "中文", "ko": "한국어"}[x],
                horizontal=True,
                key=f"comment_lang_{test['id']}",
            )
            new_comment = st.text_area(
                " ",
                value=cur_comment,
                placeholder=t("test_lab.comment_placeholder"),
                height=80,
                key=f"comment_{test['id']}",
                label_visibility="collapsed",
            )
            if st.button(
                t("test_lab.submit_verdict"),
                key=f"comment_save_{test['id']}",
            ):
                update_test_verdict(
                    test["id"],
                    test.get("verdict") or "pending",
                    new_comment.strip() or None,
                    new_lang,
                )
                st.toast("Saved", icon="✅")
                st.rerun()


def render() -> None:
    hero(
        title=t("test_lab.title"),
        subtitle=t("test_lab.subtitle"),
        eyebrow="🧪",
    )

    forms = list_forms()
    if not forms:
        st.info(t("forms.no_forms"))
        return

    # Limit to forms with at least one reference take
    eligible = [f for f in forms if f["status"] in ("recorded", "ready")]
    if not eligible:
        st.warning(t("test_lab.form_not_ready"))
        return

    eligible_by_id = {f["id"]: f for f in eligible}
    form_options = {f["id"]: form_display_name(f) for f in eligible}

    def _format_option(fid: str) -> str:
        dan = eligible_by_id[fid]["dan_level"]
        return form_options[fid] + "  ·  " + t("forms.dan_" + str(dan))

    sel_id = st.selectbox(
        t("test_lab.select_form"),
        options=list(form_options.keys()),
        format_func=_format_option,
        key="test_form_select",
    )
    if not sel_id:
        return

    form = get_form(sel_id)
    st.markdown(f"### {form_display_name(form)}")

    # New test section
    with st.container(border=True):
        st.markdown(f"#### {t('test_lab.add_test')}")
        uploaded = st.file_uploader(
            t("test_lab.upload_label"),
            type=["mp4", "mov", "m4v"],
            key=f"test_upload_{sel_id}",
        )
        intent_lang = st.radio(
            t("translation.original"),
            options=["zh", "ko"],
            format_func=lambda x: {"zh": "中文", "ko": "한국어"}[x],
            horizontal=True,
            key=f"intent_lang_{sel_id}",
        )
        intent = st.text_area(
            t("test_lab.intent_label"),
            placeholder=t("test_lab.intent_placeholder"),
            height=80,
            key=f"intent_{sel_id}",
        )
        cols = st.columns([1, 1])
        expected = cols[0].radio(
            t("test_lab.expected_label"),
            options=["catch", "pass", "either"],
            format_func=lambda x: {
                "catch": t("test_lab.expected_catch"),
                "pass": t("test_lab.expected_pass"),
                "either": t("test_lab.expected_either"),
            }[x],
            key=f"expected_{sel_id}",
        )
        tags_raw = cols[1].text_input(
            t("test_lab.tags_label"),
            placeholder=t("test_lab.tags_placeholder"),
            key=f"tags_{sel_id}",
        )

        if st.button(
            t("test_lab.run_btn"),
            type="primary",
            disabled=(uploaded is None),
            key=f"run_test_{sel_id}",
            use_container_width=True,
        ):
            ext = Path(uploaded.name).suffix.lower() or ".mp4"
            video_temp_path, uid = _save_test_video_to_temp(uploaded.getvalue(), ext)
            tags = [t_.strip() for t_ in tags_raw.split(",") if t_.strip()]
            try:
                _run_scoring(
                    form_id=sel_id,
                    video_temp_path=video_temp_path,
                    uid=uid,
                    ext=ext,
                    intent=intent.strip() or None,
                    intent_lang=intent_lang,
                    expected=expected,
                    tags=tags,
                )
                st.toast("Saved", icon="✅")
                st.rerun()
            except Exception as e:
                _cleanup_temp(video_temp_path)
                st.error(f"{t('common.error')}: {e}")
            else:
                _cleanup_temp(video_temp_path)

    # Recent tests
    st.markdown("")
    head = st.columns([3, 1])
    head[0].markdown(f"### {t('test_lab.results_title')}")
    if head[1].button(
        f"🔄 {t('test_lab.rerun_all')}",
        key=f"rerun_all_{sel_id}",
        use_container_width=True,
    ):
        tests = list_tests(form_id=sel_id, limit=200)
        with st.spinner("Rescoring..."):
            for tst in tests:
                try:
                    _rerun_scoring(tst)
                except Exception:
                    pass
        st.toast("Done", icon="✅")
        st.rerun()

    tests = list_tests(form_id=sel_id, limit=50)
    if not tests:
        st.info(t("test_lab.no_tests"))
        return
    for tst in tests:
        _render_test_card(tst)
