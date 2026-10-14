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
                {"type": "text", "text": "このレシートを読んでください。date は買った日（例：2026-10-14。わからないときは空）、store はお店の名前、items は買った商品です。商品ごとに、name は商品名、reading は商品名のよみがな（ひらがな）、price は値段（円、数字だけ）、category は区分です。区分は、料理に使うものは「食材」、お茶・ジュース・水などは「飲み物」（牛乳は料理にも使うので「食材」）、ビール・酒は「お酒」、おやつは「お菓子」、洗剤・ティッシュなどは「日用品」、どれにも当てはまらないものは「その他」にしてください。値引きがあるときは、値引きしたあとの値段にしてください。小計・合計・消費税・お預り・お釣りは items に入れないでください。"},
            ],
        }],
        output_format=Receipt,
    )
    return response.parsed_output


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
        if result is not None:
            try:
                st.session_state["receipt_date"] = datetime.date.fromisoformat(result.date)
            except ValueError:
                st.session_state["receipt_date"] = datetime.date.today()
            st.session_state["receipt_store"] = result.store
            rows = [{"区分": item.category, "商品": item.name, "よみがな": item.reading, "値段": item.price} for item in result.items]
            st.session_state["receipt_rows"] = pd.DataFrame(rows)
            st.session_state.pop("receipt_editor", None)

if "receipt_rows" in st.session_state:
    st.subheader("読み取った結果（直せます）")
    st.date_input("日付", key="receipt_date")
    st.text_input("お店", key="receipt_store")
    edited = st.data_editor(
        st.session_state["receipt_rows"],
        column_config={
            "区分": st.column_config.SelectboxColumn("区分", options=CATEGORIES, required=True),
            "値段": st.column_config.NumberColumn("値段", min_value=0, step=1, format="%d円"),
        },
        hide_index=True,
        key="receipt_editor",
    )
    st.write(f"合計：{edited['値段'].sum():,}円")