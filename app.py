import streamlit as st

pages = [
    st.Page("pages/献立を作る.py", title="献立を作る", icon="🍚"),
    st.Page("pages/買い物の記録.py", title="買い物の記録", icon="🧾"),
    st.Page("pages/設定.py", title="設定", icon="⚙️"),
]
page = st.navigation(pages)
logo = st.session_state.get("logo", "images/logo_nikukyu.png")
st.set_page_config(page_title=f"{page.title}｜やりくり献立", page_icon=logo)
st.logo(logo, size="large")
page.run()