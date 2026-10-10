import streamlit as st

st.title("やりくり献立")

people = st.number_input("人数", min_value=1, max_value=10, value=2)
budget = st.number_input("1か月の食費の予算（円）", min_value=0, step=1000, value=50000)
dislikes = st.text_input("苦手な食材・アレルギー（例：えび、セロリ）")
area = st.text_input("地域（例：東京都 世田谷区）")
store = st.text_input("よく行くスーパー（例：〇〇ストア 駅前店）")

st.write("人数：", people, "人")
st.write("予算：", budget, "円")
st.write("苦手な食材：", dislikes)
st.write("地域：", area)
st.write("スーパー：", store)