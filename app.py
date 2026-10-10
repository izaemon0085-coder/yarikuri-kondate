import streamlit as st

st.title("やりくり献立")

people = st.number_input("人数", min_value=1, max_value=10, value=2)
budget = st.number_input("1か月の食費の予算（円）", min_value=0, step=1000, value=50000)
dislikes = st.text_input("苦手な食材・アレルギー（例：えび、セロリ）")
area = st.text_input("地域（例：東京都 世田谷区）")
store = st.text_input("よく行くスーパー（例：〇〇ストア 駅前店）")
sale_text = st.text_area("特売品（1行に1つ。例：豚こま 100g 98円）")

sale_items = [line.strip() for line in sale_text.splitlines() if line.strip()]

if st.button("献立を作る"):
    if sale_items:
        sale_list = "\n".join("  - " + item for item in sale_items)
    else:
        sale_list = "  - なし"

    prompt = f"""あなたは、家庭料理と食費の節約が得意な献立アドバイザーです。
次の条件で、1日分の献立（朝・昼・夜）を考えてください。

- 人数：{people}人
- 1か月の食費の予算：{budget}円
- 苦手な食材・アレルギー：{dislikes or "なし"}
- 地域：{area or "指定なし"}
- よく行くスーパー：{store or "指定なし"}
- 今週の特売品：
{sale_list}

苦手な食材・アレルギーの食材は、絶対に使わないでください。
特売品は、できるだけ使ってください。"""

    st.subheader("AIへのお願い文（確認用）")
    st.text(prompt)