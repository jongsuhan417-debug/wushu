"""Wushu Evaluation Workbench — Streamlit entry."""
import streamlit as st

from _ui import bootstrap, ensure_db_seeded, inject_css

bootstrap()

from core.i18n import init_lang, render_language_toggle, t  # noqa: E402

# Page config — must run first thing
st.set_page_config(
    page_title="武术评估工作台 / 우슈 평가 워크벤치",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="auto",
)

init_lang()
inject_css()
ensure_db_seeded()


# Sidebar: brand + language toggle (rendered before nav)
with st.sidebar:
    st.markdown(
        f"""
        <div class="brand">🥋 {t('app.brand')}</div>
        <div class="brand-sub">{t('app.tagline')}</div>
        <div style='margin-top:6px;font-size:11px;font-weight:600;
                    background:#3D2F22;color:#F4D9A6;padding:3px 8px;
                    border-radius:6px;display:inline-block'>
          {t('app.dev_badge')}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    render_language_toggle()
    st.markdown("---")


# Define pages with localized titles via callables
from pages import home, reference_studio, test_lab, forms_catalog, guide  # noqa: E402

home_page = st.Page(
    home.render,
    title=t("nav.home"),
    icon=":material/home:",
    url_path="home",
    default=True,
)
guide_page = st.Page(
    guide.render,
    title=t("nav.guide"),
    icon=":material/menu_book:",
    url_path="guide",
)
ref_page = st.Page(
    reference_studio.render,
    title=t("nav.reference_studio"),
    icon=":material/videocam:",
    url_path="reference",
)
test_page = st.Page(
    test_lab.render,
    title=t("nav.test_lab"),
    icon=":material/science:",
    url_path="test-lab",
)
forms_page = st.Page(
    forms_catalog.render,
    title=t("nav.forms_catalog"),
    icon=":material/list_alt:",
    url_path="forms",
)

# Expose Page objects so other pages can build st.page_link buttons.
st.session_state["_pages"] = {
    "home": home_page,
    "guide": guide_page,
    "reference": ref_page,
    "test_lab": test_page,
    "forms_catalog": forms_page,
}

nav = st.navigation(
    [home_page, guide_page, ref_page, test_page, forms_page],
    position="sidebar",
)
nav.run()
