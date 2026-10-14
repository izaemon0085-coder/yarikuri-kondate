import streamlit as st

pages = [
    st.Page("pages/献立を作る.py"),
    st.Page("pages/買い物の記録.py"),
]
st.navigation(pages).run()