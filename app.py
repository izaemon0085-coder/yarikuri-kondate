import streamlit as st

st.title("やりくり献立")

people = st.number_input("人数", min_value=1, max_value=10, value=2)
budget = st.number_input("1か月の食費の予算（円）", min_value=0, step=1000, value=50000)

st.write("人数：", people, "人")
st.write("予算：", budget, "円")