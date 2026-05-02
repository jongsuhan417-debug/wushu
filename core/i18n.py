"""Bilingual (ko/zh) UI string loader and helpers."""
from pathlib import Path
import yaml
import streamlit as st

from .paths import I18N_DIR

LANGS = ("ko", "zh")
LANG_LABELS = {"ko": "한국어", "zh": "中文"}
LANG_FLAGS = {"ko": "KR", "zh": "CN"}
DEFAULT_LANG = "ko"


@st.cache_resource
def _load_translations() -> dict:
    out = {}
    for lang in LANGS:
        path = I18N_DIR / f"{lang}.yaml"
        if path.exists():
            out[lang] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        else:
            out[lang] = {}
    return out


def init_lang() -> None:
    if "lang" not in st.session_state:
        st.session_state["lang"] = DEFAULT_LANG


def current_lang() -> str:
    init_lang()
    return st.session_state["lang"]


def set_lang(lang: str) -> None:
    if lang in LANGS:
        st.session_state["lang"] = lang


def t(key: str, **kwargs) -> str:
    """Translate dot-separated key with current language. Falls back to the key itself."""
    init_lang()
    translations = _load_translations()
    lang = current_lang()

    def lookup(d, key_path):
        node = d
        for part in key_path:
            if not isinstance(node, dict):
                return None
            node = node.get(part)
            if node is None:
                return None
        return node

    parts = key.split(".")
    value = lookup(translations.get(lang, {}), parts)
    if value is None and lang != DEFAULT_LANG:
        value = lookup(translations.get(DEFAULT_LANG, {}), parts)
    if value is None:
        return key
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError):
            return value
    return value if isinstance(value, str) else str(value)


def render_language_toggle(container=None) -> None:
    """Render compact language toggle. Defaults to sidebar."""
    init_lang()
    container = container if container is not None else st.sidebar

    cols = container.columns(2)
    for i, lang in enumerate(LANGS):
        is_current = st.session_state["lang"] == lang
        label = f"{LANG_FLAGS[lang]}  {LANG_LABELS[lang]}"
        if cols[i].button(
            label,
            use_container_width=True,
            type=("primary" if is_current else "secondary"),
            key=f"lang_btn_{lang}",
        ):
            if not is_current:
                set_lang(lang)
                st.rerun()
