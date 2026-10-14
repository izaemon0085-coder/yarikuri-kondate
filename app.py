
import streamlit as st

pages = [
    st.Page("pages/献立を作る.py", title="献立を作る", icon="🍚"),
    st.Page("pages/買い物の記録.py", title="買い物の記録", icon="🧾"),
]
st.navigation(pages).run()