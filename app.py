import streamlit as st
from streamlit import config

from themes import THEMES

pages = [
    st.Page("pages/献立を作る.py", title="献立を作る", icon="🍚"),
    st.Page("pages/買い物の記録.py", title="買い物の記録", icon="🧾"),
    st.Page("pages/設定.py", title="設定", icon="⚙️"),
]
page = st.navigation(pages)

color = st.session_state.get("color", "緑")
changed = Falsep
for name, value in THEMES[color].items():
    if config.get_option(f"theme.{name}") != value:
        config.set_option(f"theme.{name}", value)
        changed = True
if changed:
    st.rerun()

logo = st.session_state.get("logo", "images/logo_nikukyu.png")
st.set_page_config(page_title=f"{page.title}｜やりくり献立", page_icon=logo)
st.logo(logo, size="large")
page.run()