import base64
import datetime
import io
from typing import Literal

import anthropic
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel

load_dotenv()
client = anthropic.Anthropic()

CATEGORIES = ["食材", "飲み物", "お酒", "お菓子", "日用品", "その他"]
SORT_ORDERS = ["レシートの順", "あいうえお順", "区分ごと", "値段の高い順", "値段の安い順"]


class ReceiptItem(BaseModel):
    name: str
    reading: str
    price: int
    category: Literal["食材", "飲み物", "お酒", "お菓子", "日用品", "その他"]


class Receipt(BaseModel):
    date: str
    store: str
    items: list[ReceiptItem]


def read_receipt(file):
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
                {"type": "text", "text": "このレシートを読んでください。date は買った日（例：2026-10-14。わからないときは空）、store はお店の名前、items は買った商品です。商品ごとに、name は商品名、reading は商品名のよみがな（ひらがな）、price は値段（円、数字だけ）、category は区分です。区分は、料理に使うものは「食材」、お茶・ジュース・水などは「飲み物」（牛乳は料理にも使うので「食材」）、ビール・酒は「お酒」、おやつは「お菓子」、洗剤・ティッシュなどは「日用品」、どれにも当てはまらないものは「その他」にしてください。値引きがあるときは、値引きしたあとの値段にしてください。小計・合計・消費税・お預り・お釣りは items に入れないでください。レシートではない写真や、商品が見つからないときは、items を空にしてください。"},
            ],
        }],
        output_format=Receipt,
    )
    result = response.parsed_output
    if result is None:
        return Receipt(date="", store="", items=[])
    return result


def sort_rows(rows, order, category_order):
    rows = rows.sort_values("順番")
    if order == "あいうえお順":
        return rows.sort_values("よみがな", kind="stable")
    if order == "区分ごと":
        return rows.sort_values("区分", key=lambda column: column.map(category_order.index), kind="stable")
    if order == "値段の高い順":
        return rows.sort_values("値段", ascending=False, kind="stable")
    if order == "値段の安い順":
        return rows.sort_values("値段", kind="stable")
    return rows


st.title("買い物の記録")
st.write("ここで、レシートの読み取りや、買い物の記録をします。")

receipt = st.file_uploader("レシートの写真（JPG・PNG）", type=["jpg", "jpeg", "png"])
if receipt is not None:
    st.image(receipt, caption=receipt.name, width=300)
    if st.button("レシートを読み取る"):
        with st.spinner("AIがレシートを読んでいます…"):
            try:
                result = read_receipt(receipt)
            except anthropic.APIError:
                result = None
                st.error("レシートを読み取れませんでした。少し待ってから、もう一度試してください。")
        if result is not None and not result.items:
            st.session_state.pop("receipt_rows", None)
            st.warning("レシートが見つかりませんでした。お店のレシートの写真か確認してください。")
        elif result is not None:
            try:
                st.session_state["receipt_date"] = datetime.date.fromisoformat(result.date)
            except ValueError:
                st.session_state["receipt_date"] = datetime.date.today()
            st.session_state["receipt_store"] = result.store
            rows = [{"順番": number, "区分": item.category, "商品": item.name, "よみがな": item.reading, "値段": item.price} for number, item in enumerate(result.items, start=1)]
            st.session_state["receipt_rows"] = pd.DataFrame(rows)
            st.session_state["editor_version"] = st.session_state.get("editor_version", 0) + 1

if "receipt_rows" in st.session_state:
    st.subheader("読み取った結果（直せます）")
    st.date_input("日付", key="receipt_date")
    st.text_input("お店", key="receipt_store")
    order = st.selectbox("並べ方", SORT_ORDERS)
    chosen = st.multiselect("区分の順番（「区分ごと」のとき、選んだ順に並びます）", CATEGORIES, default=CATEGORIES)
    category_order = chosen + [category for category in CATEGORIES if category not in chosen]
    rows = sort_rows(st.session_state["receipt_rows"], order, category_order)
    editor_key = f"receipt_editor_{st.session_state['editor_version']}"
    edited = st.data_editor(
        rows,
        column_config={
            "区分": st.column_config.SelectboxColumn("区分", options=CATEGORIES, required=True),
            "値段": st.column_config.NumberColumn("値段", min_value=0, step=1, format="%d円"),
        },
        column_order=["区分", "商品", "よみがな", "値段"],
        hide_index=True,
        key=editor_key,
    )
    changes = st.session_state[editor_key]
    if changes["edited_rows"]:
        st.session_state["receipt_rows"] = edited
        st.session_state["editor_version"] += 1
        st.rerun()
    st.write(f"合計：{edited['値段'].sum():,}円")