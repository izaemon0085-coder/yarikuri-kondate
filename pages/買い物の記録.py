import base64
import datetime
import io
from pathlib import Path
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
COLUMNS = ["順番", "区分", "商品", "よみがな", "値段"]
RECORD_FILE = Path(__file__).parent.parent / "kaimono.csv"


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


def set_receipt(date, store, rows):
    st.session_state["receipt_date"] = date
    st.session_state["receipt_store"] = store
    st.session_state["receipt_rows"] = pd.DataFrame(rows, columns=COLUMNS)
    st.session_state["editor_version"] = st.session_state.get("editor_version", 0) + 1


def fill_new_rows(rows):
    rows = rows.copy()
    last_number = rows["順番"].max()
    if pd.isna(last_number):
        last_number = 0
    rows["順番"] = rows["順番"].fillna(last_number + 1)
    rows["よみがな"] = rows["よみがな"].fillna("")
    no_reading = rows["よみがな"] == ""
    rows.loc[no_reading, "よみがな"] = rows.loc[no_reading, "商品"].fillna("")
    return rows


def load_records():
    if RECORD_FILE.exists():
        return pd.read_csv(RECORD_FILE)
    return pd.DataFrame(columns=["日付", "お店", "区分", "商品", "よみがな", "値段"])


def write_records(records):
    records.to_csv(RECORD_FILE, index=False, encoding="utf-8-sig")


def save_records(date, store, rows):
    rows = rows.sort_values("順番")
    new_records = pd.DataFrame({
        "日付": date.isoformat(),
        "お店": store,
        "区分": rows["区分"],
        "商品": rows["商品"],
        "よみがな": rows["よみがな"],
        "値段": rows["値段"].astype(int),
    })
    records = pd.concat([load_records(), new_records], ignore_index=True)
    write_records(records)


st.title("買い物の記録")
st.write("ここで、レシートの読み取りや、買い物の記録をします。")

if "saved_message" in st.session_state:
    st.success(st.session_state.pop("saved_message"))

st.sidebar.header("表の並べ方")
order = st.sidebar.selectbox("並べ方", SORT_ORDERS)
chosen = st.sidebar.multiselect("区分の順番（「区分ごと」のとき、選んだ順に並びます）", CATEGORIES, default=CATEGORIES)
category_order = chosen + [category for category in CATEGORIES if category not in chosen]

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
                receipt_date = datetime.date.fromisoformat(result.date)
            except ValueError:
                receipt_date = datetime.date.today()
            rows = [{"順番": number, "区分": item.category, "商品": item.name, "よみがな": item.reading, "値段": item.price} for number, item in enumerate(result.items, start=1)]
            set_receipt(receipt_date, result.store, rows)

if st.button("写真なしで、新しく手で入力する"):
    set_receipt(datetime.date.today(), "", [])

if "receipt_rows" in st.session_state:
    st.subheader("買い物の内容（直せます）")
    st.date_input("日付", key="receipt_date")
    st.text_input("お店", key="receipt_store")
    rows = sort_rows(st.session_state["receipt_rows"], order, category_order)
    editor_key = f"receipt_editor_{st.session_state['editor_version']}"
    edited = st.data_editor(
        rows,
        column_config={
            "区分": st.column_config.SelectboxColumn("区分", options=CATEGORIES, required=True, default="食材"),
            "値段": st.column_config.NumberColumn("値段", min_value=0, step=1, format="%d円"),
        },
        column_order=["区分", "商品", "よみがな", "値段"],
        hide_index=True,
        num_rows="dynamic",
        key=editor_key,
    )
    st.caption("表の下の「＋」で行を足せます。よみがなが空なら、商品名が入ります（あとで直せます）。")
    changes = st.session_state[editor_key]
    if changes["edited_rows"] or changes["added_rows"] or changes["deleted_rows"]:
        st.session_state["receipt_rows"] = fill_new_rows(edited)
        st.session_state["editor_version"] += 1
        st.rerun()
    st.write(f"合計：{int(edited['値段'].sum()):,}円")

    if st.button("記録する", type="primary"):
        rows = st.session_state["receipt_rows"]
        if rows.empty:
            st.warning("記録する商品がありません。表に行を足してください。")
        elif rows["商品"].isna().any() or (rows["商品"] == "").any() or rows["値段"].isna().any():
            st.warning("商品か値段が空の行があります。入れるか、その行を消してください。")
        else:
            save_records(st.session_state["receipt_date"], st.session_state["receipt_store"], rows)
            st.session_state.pop("receipt_rows")
            st.session_state["saved_message"] = f"{len(rows)}件を記録しました。"
            st.rerun()

st.divider()
st.subheader("今月の記録")
records = load_records()
this_month = records[records["日付"].str.startswith(datetime.date.today().strftime("%Y-%m"))]
if this_month.empty:
    st.info("今月の記録は、まだありません。")
else:
    month_rows = this_month.sort_values("日付", kind="stable")
    month_rows = month_rows.assign(順番=range(len(month_rows)))
    shown = sort_rows(month_rows, order, category_order)
    table_key = f"records_table_{st.session_state.get('records_version', 0)}"
    table = st.dataframe(
        shown,
        column_config={"値段": st.column_config.NumberColumn("値段", format="%d円")},
        column_order=["日付", "お店", "区分", "商品", "値段"],
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key=table_key,
    )
    st.caption("消したい記録は、表の左はしをクリックして選んでください。")
    selected = table.selection.rows
    if st.button(f"選んだ記録を消す（{len(selected)}件）", disabled=not selected):
        write_records(records.drop(shown.index[selected]))
        st.session_state["records_version"] = st.session_state.get("records_version", 0) + 1
        st.session_state["saved_message"] = f"{len(selected)}件の記録を消しました。"
        st.rerun()

st.caption(f"これまでの記録：{len(load_records())}件")