import base64
import datetime
import io

import anthropic
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel

load_dotenv()
client = anthropic.Anthropic()


class DayMenu(BaseModel):
    date: str
    breakfast: str
    lunch: str
    dinner: str
    cost: int


class ShoppingItem(BaseModel):
    store: str
    item: str
    reason: str


class MenuPlan(BaseModel):
    days: list[DayMenu]
    shopping: list[ShoppingItem]


class SaleItem(BaseModel):
    name: str
    amount: str
    price: int


class SaleList(BaseModel):
    items: list[SaleItem]


def read_flyer(file):
    image = Image.open(file).convert("RGB")
    image.thumbnail((2000, 2000))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    image_data = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")

    response = client.beta.messages.parse(
        model="claude-opus-5-5",
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
                {"type": "text", "text": "このチラシに載っている特売品を、1つずつ答えてください。name は商品名、amount は量（例：100g、1玉、10個入り。わからないときは空）、price は値段（円、数字だけ）です。チラシではない写真や、特売品が見つからないときは、items を空にしてください。"},
            ],
        }],
        output_format=SaleList,
    )
    result = response.parsed_output
    if result is None:
        return []
    lines = []
    for item in result.items:
        parts = [item.name, item.amount, f"{item.price}円"]
        lines.append(" ".join(part for part in parts if part))
    return lines


st.title("やりくり献立")

people = st.number_input("人数", min_value=1, max_value=10, value=None, placeholder="例：2")
budget = st.number_input("1か月の食費の予算（円）", min_value=0, step=1000, value=None, placeholder="例：50000")
dislikes = st.text_input("苦手な食材・アレルギー（例：えび、セロリ）")
area = st.text_input("地域（例：東京都 世田谷区）")
store_count = st.number_input("よく行くお店の数", min_value=1, max_value=3, value=2)
stores = []
for i in range(1, store_count + 1):
    with st.container(border=True):
        name = st.text_input(f"お店{i}の名前（例：〇〇ストア 駅前店）", key=f"store_name_{i}")
        flyer = st.file_uploader(f"お店{i}のチラシの写真（JPG・PNG）", type=["jpg", "jpeg", "png"], key=f"flyer_{i}")
        if flyer is not None:
            st.image(flyer, caption=flyer.name, width=300)
            if st.button(f"お店{i}のチラシを読み取る", key=f"read_{i}"):
                with st.spinner("AIがチラシを読んでいます…"):
                    try:
                        lines = read_flyer(flyer)
                    except anthropic.APIError:
                        lines = None
                        st.error("チラシを読み取れませんでした。少し待ってから、もう一度試してください。")
                if lines == []:
                    st.warning("特売品が見つかりませんでした。スーパーのチラシの写真か確認してください。")
                elif lines:
                    current = st.session_state.get(f"sale_text_{i}", "").strip()
                    new_text = "\n".join(lines)
                    st.session_state[f"sale_text_{i}"] = f"{current}\n{new_text}" if current else new_text
                    st.success(f"{len(lines)}件の特売品を、お店{i}の特売品の欄に入れました。")
        text = st.text_area(f"お店{i}の特売品（1行に1つ。例：豚こま 100g 98円）", key=f"sale_text_{i}")
    items = [line.strip() for line in text.splitlines() if line.strip()]
    stores.append({"name": name or f"お店{i}", "items": items})

period = st.radio("献立の期間", ["1日分", "1週間分", "1か月分"])
start_date = st.date_input("献立を始める日", value=datetime.date.today())

days = {"1日分": 1, "1週間分": 7, "1か月分": 30}[period]

if st.button("献立を作る"):
    if people is None or not budget:
        st.warning("人数と1か月の食費の予算を入力してください。")
        st.stop()

    period_budget = budget * days // 30
    weekday = "月火水木金土日"[start_date.weekday()]
    start_text = f"{start_date.year}年{start_date.month}月{start_date.day}日（{weekday}）"

    store_text = ""
    for store in stores:
        store_text += f"  - {store['name']}\n"
        if store["items"]:
            for item in store["items"]:
                store_text += f"    - {item}\n"
        else:
            store_text += "    - 特売品なし\n"

    prompt = f"""あなたは、家庭料理と食費の節約が得意な献立アドバイザーです。
次の条件で、{period}の献立（朝・昼・夜）を考えてください。
献立は、{start_text}から始めてください。

- 人数：{people}人
- 1か月の食費の予算：{budget}円（{period}の目安：{period_budget}円）
- 苦手な食材・アレルギー：{dislikes or "なし"}
- 地域：{area or "指定なし"}
- よく行くお店と、今週の特売品：
{store_text}
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
- cost：その日の食費の目安（円、数字だけ）

さらに、献立に使う主な食材を、どのお店で買うと安いかを考えて、shopping に入れてください。
同じ商品が2つ以上のお店の特売品にあるときは、安いほうのお店にしてください。
特売品にない食材は、よく行くお店のどれかにしてください。
- store：お店の名前（上に書いたお店の名前のどれか）
- item：買うもの（量もあれば短く）
- reason：そのお店にした理由（例：88円で一番安い）"""

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

    st.subheader("お店ごとの買い物リスト")
    if not plan.shopping:
        st.info("買い物リストはありません。")
    else:
        store_names = []
        for s in plan.shopping:
            if s.store not in store_names:
                store_names.append(s.store)

        columns = st.columns(len(store_names))
        for column, store_name in zip(columns, store_names):
            with column:
                with st.container(border=True):
                    st.markdown(f"**{store_name}**")
                    for s in plan.shopping:
                        if s.store == store_name:
                            st.write(f"・{s.item}")
                            st.caption(s.reason)