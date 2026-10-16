import base64
import calendar
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


class Idea(BaseModel):
    title: str
    detail: str
    saving: int


class IdeaList(BaseModel):
    ideas: list[Idea]


class Fix(BaseModel):
    number: int
    reading: str
    category: Literal["食材", "飲み物", "お酒", "お菓子", "日用品", "その他"]
    reason: str


class FixList(BaseModel):
    fixes: list[Fix]


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


def ask_ideas(prompt):
    response = client.beta.messages.parse(
        model="claude-opus-5-5",
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
        output_format=IdeaList,
    )
    result = response.parsed_output
    if result is None:
        return []
    return result.ideas


def check_items(rows):
    rows = rows.reset_index(drop=True)
    lines = ""
    for number, row in rows.iterrows():
        lines += f"  {number}: 商品「{row['商品']}」 よみがな「{row['よみがな']}」 区分「{row['区分']}」\n"
    prompt = f"""あなたは、レシートの読み取り結果を確認する係です。
下の表は、別のAIがレシートから読み取ったものです。一つずつ、よみがなと区分が正しいか確認してください。

- よみがな：商品名のひらがなの読み方が合っているか（例：牛乳→ぎゅうにゅう）
- 区分：食材・飲み物・お酒・お菓子・日用品・その他 のどれが合っているか
    料理に使うものは「食材」、お茶・ジュース・水などは「飲み物」（牛乳は料理にも使うので「食材」）、
    ビール・酒は「お酒」、おやつは「お菓子」、洗剤・ティッシュなどは「日用品」、
    どれにも当てはまらないものは「その他」です。

読み取り結果：
{lines}
直したほうがよい商品だけを、fixes に入れてください。合っている商品は入れないでください。
- number：その商品の番号（上の表の番号）
- reading：正しいよみがな（ひらがな）
- category：正しい区分
- reason：なぜ直すとよいか（短く）"""
    response = client.beta.messages.parse(
        model="claude-opus-5-5",
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
        output_format=FixList,
    )
    result = response.parsed_output
    if result is None:
        return []
    return [fix for fix in result.fixes if 0 <= fix.number < len(rows)]


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
st.caption("レシートの写真や手入力で、使った金額を記録します。今月の合計や、予算との比べ方も見られます。")

if "saved_message" in st.session_state:
    st.success(st.session_state.pop("saved_message"))

st.sidebar.header("表の並べ方")
order = st.sidebar.selectbox("並べ方", SORT_ORDERS)
chosen = st.sidebar.multiselect("区分の順番（「区分ごと」のとき、選んだ順に並びます）", CATEGORIES, default=CATEGORIES)
category_order = chosen + [category for category in CATEGORIES if category not in chosen]

st.subheader("1. 買い物を入力する")
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
        st.session_state.pop("fixes", None)
        st.rerun()
    st.write(f"合計：{int(edited['値段'].sum()):,}円")

    if st.button("確認役AIにチェックしてもらう"):
        base = st.session_state["receipt_rows"].sort_values("順番").reset_index(drop=True)
        with st.spinner("確認役AIがチェックしています…"):
            try:
                st.session_state["fixes"] = check_items(base)
            except anthropic.APIError:
                st.error("チェックできませんでした。少し待ってから、もう一度試してください。")
        st.rerun()

    if "fixes" in st.session_state:
        fixes = st.session_state["fixes"]
        if not fixes:
            st.success("確認役AIのチェック：直したほうがよいところは、見つかりませんでした。")
        else:
            st.warning(f"確認役AIが、{len(fixes)}件、直したほうがよいところを見つけました。")

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
st.subheader("2. 今月の記録")
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

    st.divider()
    st.subheader("3. 今月の合計")
    st.write(f"**今月の合計：{this_month['値段'].sum():,}円**")
    column1, column2 = st.columns(2)
    with column1:
        st.markdown("**区分ごと**")
        totals = this_month.groupby("区分")["値段"].sum().reindex(category_order, fill_value=0)
        st.table(pd.DataFrame({"合計": [f"{total:,}円" for total in totals]}, index=totals.index))
    with column2:
        st.markdown("**お店ごと**")
        store_names = this_month["お店"].fillna("（お店の名前なし）")
        store_totals = this_month["値段"].groupby(store_names).sum().sort_values(ascending=False)
        st.table(pd.DataFrame({"合計": [f"{total:,}円" for total in store_totals]}, index=store_totals.index.rename("お店")))

st.divider()
st.subheader("4. 食費の予算（今月）")
budget = st.number_input("1か月の食費の予算（円）", min_value=0, step=1000, value=None, placeholder="例：50000")
food_total = int(this_month.loc[this_month["区分"].isin(["食材", "飲み物"]), "値段"].sum())
if budget is None:
    st.info("予算を入れると、残りの金額が出ます。")
else:
    remaining = budget - food_total
    today = datetime.date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = days_in_month - today.day + 1
    column1, column2, column3 = st.columns(3)
    column1.metric("予算", f"{budget:,}円")
    column2.metric("使った食費（食材＋飲み物）", f"{food_total:,}円")
    column3.metric("残り", f"{remaining:,}円")
    if remaining >= 0:
        st.write(f"今月はあと{days_left}日です。1日あたり、約{remaining // days_left:,}円 使えます。")
    else:
        st.write(f"予算を{-remaining:,}円 こえています。今月はあと{days_left}日です。")

    projected = food_total * days_in_month // today.day
    if projected <= budget:
        st.write(f"このままのペースだと、月末の食費は約{projected:,}円です。予算内におさまりそうです。")
    else:
        st.write(f"このままのペースだと、月末の食費は約{projected:,}円です。予算を少しこえそうです。")
        if st.button("安く済ませる案を、AIに聞く"):
            food_rows = this_month[this_month["区分"].isin(["食材", "飲み物"])]
            lines = ""
            for _, row in food_rows.iterrows():
                lines += f"  - {row['日付']} {row['お店']} {row['商品']} {row['値段']}円\n"
            prompt = f"""あなたは、家庭料理と食費の節約が得意なアドバイザーです。
今月の食費が、予算をこえそうです。注意や警告ではなく、前向きで具体的な「代わりの案」を3つから5つ出してください。

- 1か月の食費の予算：{budget}円
- 今月使った食費：{food_total}円（今日まで{today.day}日間）
- このままのペースだと、月末に：約{projected}円
- 予算の残り：{remaining}円（今月はあと{days_left}日）
- 今月買った食材と飲み物（日付 お店 商品 値段）：
{lines}
案は、次のようなものにしてください。
- 高い食材を、安くて似た食材に置きかえる（例：鶏もも肉を鶏むね肉に）
- 同じ商品がもっと安いお店があれば、そのお店で買う
- 安い食材（もやし・豆腐・卵など）を使った料理を増やす
上の記録にある値段は、そのまま使ってください。記録にない値段は、実際のスーパーの値段に近い金額にしてください。

案ごとに、次の3つを答えてください。
- title：案の短い見出し（例：鶏もも肉を鶏むね肉に）
- detail：具体的なやり方（2〜3文）
- saving：今月の残りの日で、だいたい何円安くなるか（円、数字だけ）"""
            with st.spinner("AIが案を考えています…"):
                try:
                    ideas = ask_ideas(prompt)
                except anthropic.APIError:
                    ideas = None
                    st.error("案を受け取れませんでした。少し待ってから、もう一度試してください。")
            if ideas == []:
                st.info("案が見つかりませんでした。もう一度試してください。")
            elif ideas:
                st.subheader("💡 安く済ませる案")
                for idea in ideas:
                    with st.container(border=True):
                        st.markdown(f"**{idea.title}**")
                        st.write(idea.detail)
                        st.caption(f"今月の残りで、約{idea.saving:,}円 安くなります")

st.caption(f"これまでの記録：{len(load_records())}件")