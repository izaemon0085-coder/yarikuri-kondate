from pathlib import Path

import streamlit as st
from streamlit import config

from themes import THEMES
from user_settings import load_settings

DEFAULT_LOGO = "images/logo_nikukyu.png"
DEFAULT_COLOR = "緑"

pages = [
    st.Page("pages/献立を作る.py", title="献立を作る", icon="🍚"),
    st.Page("pages/買い物の記録.py", title="買い物の記録", icon="🧾"),
    st.Page("pages/設定.py", title="設定", icon="⚙️"),
]
page = st.navigation(pages)

if "logo" not in st.session_state:
    saved = load_settings()
    st.session_state["logo"] = saved.get("logo", DEFAULT_LOGO)
    st.session_state["color"] = saved.get("color", DEFAULT_COLOR)
if not Path(st.session_state["logo"]).exists():
    st.session_state["logo"] = DEFAULT_LOGO
if st.session_state["color"] not in THEMES:
    st.session_state["color"] = DEFAULT_COLOR

color = st.session_state["color"]
changed = False
for name, value in THEMES[color].items():
    if config.get_option(f"theme.{name}") != value:
        config.set_option(f"theme.{name}", value)
        changed = True
if changed:
    st.rerun()

logo = st.session_state["logo"]
st.set_page_config(page_title=f"{page.title}｜やりくり献立", page_icon=logo)
st.logo(logo, size="large")
page.run()