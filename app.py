import re

import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

st.title("やりくり献立")

people = st.number_input("人数", min_value=1, max_value=10, value=2)
budget = st.number_input("1か月の食費の予算（円）", min_value=0, step=1000, value=50000)
dislikes = st.text_input("苦手な食材・アレルギー（例：えび、セロリ）")
area = st.text_input("地域（例：東京都 世田谷区）")
store = st.text_input("よく行くスーパー（例：〇〇ストア 駅前店）")
sale_text = st.text_area("特売品（1行に1つ。例：豚こま 100g 98円）")
period = st.radio("献立の期間", ["1日分", "1週間分", "1か月分"])

sale_items = [line.strip() for line in sale_text.splitlines() if line.strip()]

days = {"1日分": 1, "1週間分": 7, "1か月分": 30}[period]
period_budget = budget * days // 30

if st.button("献立を作る"):
    if sale_items:
        sale_list = "\n".join("  - " + item for item in sale_items)
    else:
        sale_list = "  - なし"

    prompt = f"""あなたは、家庭料理と食費の節約が得意な献立アドバイザーです。
次の条件で、{period}の献立（朝・昼・夜）を考えてください。

- 人数：{people}人
- 1か月の食費の予算：{budget}円（{period}の目安：{period_budget}円）
- 苦手な食材・アレルギー：{dislikes or "なし"}
- 地域：{area or "指定なし"}
- よく行くスーパー：{store or "指定なし"}
- 今週の特売品：
{sale_list}

苦手な食材・アレルギーの食材は、絶対に使わないでください。
特売品は、できるだけ使ってください。

1週間分のときは1日目〜7日目まで、1か月分のときは1日目〜30日目まで、毎日の献立を書いてください。
同じ料理が続かないようにしてください。

答えは、日ごとに見出しをつけて、朝・昼・夜の料理名と主な材料を短く書いてください。
各日の最後に「この日の食費：約○○円」と書いてください。
一番最後に「合計：約○○円」と1行で書いてください。"""

    with st.expander("AIへのお願い文（確認用）"):
        st.text(prompt)

    st.subheader(f"{period}の献立")
    with st.spinner("AIが献立を考えています…"):
        with client.beta.messages.stream(
            model="claude-opus-5-5",
            max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            menu_text = st.write_stream(stream.text_stream)

    totals = re.findall(r"合計[:：]\s*約?([\d,]+)円", menu_text)
    if totals:
        total = int(totals[-1].replace(",", ""))
        if total <= period_budget:
            st.success(f"予算内です（合計 約{total:,}円 ／ 目安 {period_budget:,}円）")
        else:
            st.error(f"予算オーバーです（合計 約{total:,}円 ／ 目安 {period_budget:,}円）")
    else:
        st.warning("合計金額を読み取れませんでした")