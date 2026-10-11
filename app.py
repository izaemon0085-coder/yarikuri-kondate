import datetime

import anthropic
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
client = anthropic.Anthropic()


class DayMenu(BaseModel):
    date: str
    breakfast: str
    lunch: str
    dinner: str
    cost: int


class MenuPlan(BaseModel):
    days: list[DayMenu]


st.title("やりくり献立")

people = st.number_input("人数", min_value=1, max_value=10, value=None, placeholder="例：2")
budget = st.number_input("1か月の食費の予算（円）", min_value=0, step=1000, value=None, placeholder="例：50000")
dislikes = st.text_input("苦手な食材・アレルギー（例：えび、セロリ）")
area = st.text_input("地域（例：東京都 世田谷区）")
store = st.text_input("よく行くスーパー（例：〇〇ストア 駅前店）")
flyer = st.file_uploader("チラシの写真（JPG・PNG）", type=["jpg", "jpeg", "png"])
if flyer is not None:
    st.image(flyer, caption=flyer.name, width=300)

sale_text = st.text_area("特売品（1行に1つ。例：豚こま 100g 98円）")
period = st.radio("献立の期間", ["1日分", "1週間分", "1か月分"])
start_date = st.date_input("献立を始める日", value=datetime.date.today())

sale_items = [line.strip() for line in sale_text.splitlines() if line.strip()]

days = {"1日分": 1, "1週間分": 7, "1か月分": 30}[period]

if st.button("献立を作る"):
    if people is None or not budget:
        st.warning("人数と1か月の食費の予算を入力してください。")
        st.stop()

    period_budget = budget * days // 30
    weekday = "月火水木金土日"[start_date.weekday()]
    start_text = f"{start_date.year}年{start_date.month}月{start_date.day}日（{weekday}）"

    if sale_items:
        sale_list = "\n".join("  - " + item for item in sale_items)
    else:
        sale_list = "  - なし"

    prompt = f"""あなたは、家庭料理と食費の節約が得意な献立アドバイザーです。
次の条件で、{period}の献立（朝・昼・夜）を考えてください。
献立は、{start_text}から始めてください。

- 人数：{people}人
- 1か月の食費の予算：{budget}円（{period}の目安：{period_budget}円）
- 苦手な食材・アレルギー：{dislikes or "なし"}
- 地域：{area or "指定なし"}
- よく行くスーパー：{store or "指定なし"}
- 今週の特売品：
{sale_list}

苦手な食材・アレルギーの食材は、絶対に使わないでください。
特売品は、できるだけ使ってください。

{days}日分すべての献立を、同じ料理が続かないように考えてください。
できるだけ予算内に収まるように、料理や材料を工夫してください。
食費は、実際のスーパーの値段に近い金額にしてください。
予算が足りないときも、金額を小さく書かずに、正直な金額を書いてください。

1日ごとに、次の5つを答えてください。
- date：日付（例：2026-10-12）
- breakfast：朝の料理名（主な材料をかっこで短く）
- lunch：昼の料理名（主な材料をかっこで短く）
- dinner：夜の料理名（主な材料をかっこで短く）
- cost：その日の食費の目安（円、数字だけ）"""

    with st.expander("AIへのお願い文（確認用）"):
        st.text(prompt)

    st.subheader(f"{period}の献立")
    with st.spinner("AIが献立を考えています…"):
        try:
            with client.beta.messages.stream(
                model="claude-opus-5-5",
                max_tokens=64000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                messages=[{"role": "user", "content": prompt}],
                output_format=MenuPlan,
            ) as stream:
                plan = stream.get_final_message().parsed_output
        except anthropic.AuthenticationError:
            st.error("APIキーが正しくないか、期限が切れています。.env を確認してください。")
            st.stop()
        except anthropic.APIConnectionError:
            st.error("インターネットに接続できませんでした。接続を確認してください。")
            st.stop()
        except anthropic.APIStatusError as e:
            st.error(f"AIでエラーが起きました（{e.status_code}）。少し待ってから、もう一度試してください。")
            st.stop()

    if plan is None:
        st.warning("献立のデータを受け取れませんでした。もう一度試してください。")
        st.stop()

    rows = []
    for day in plan.days:
        d = datetime.date.fromisoformat(day.date)
        day_weekday = "月火水木金土日"[d.weekday()]
        rows.append({
            "日付": f"{d.month}/{d.day}({day_weekday})",
            "朝": day.breakfast,
            "昼": day.lunch,
            "夜": day.dinner,
            "食費": f"約{day.cost:,}円",
        })

    total = sum(day.cost for day in plan.days)
    if total <= period_budget:
        st.success(f"予算内です（合計 約{total:,}円 ／ 目安 {period_budget:,}円）")
    else:
        st.error(f"予算オーバーです（合計 約{total:,}円 ／ 目安 {period_budget:,}円）")

    weeks = [rows[i:i + 7] for i in range(0, len(rows), 7)]
    tab_names = [f"第{n}週（{week[0]['日付']}〜）" for n, week in enumerate(weeks, start=1)]
    tabs = st.tabs(tab_names)
    for tab, week in zip(tabs, weeks):
        with tab:
            st.table(pd.DataFrame(week).set_index("日付"))