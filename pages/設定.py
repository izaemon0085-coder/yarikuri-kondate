from pathlib import Path

import streamlit as st

from themes import THEMES

LOGO_NAMES = {
    "logo_nikukyu.png": "猫の肉球",
    "logo_ochawan.png": "お茶碗",
    "logo_kago.png": "買い物かご",
    "logo_neko.png": "猫",
}


def logo_name(logo):
    return LOGO_NAMES.get(Path(logo).name, Path(logo).stem)


def choose_logo():
    st.session_state["logo"] = st.session_state["logo_choice"]


def choose_color():
    st.session_state["color"] = st.session_state["color_choice"]


st.title("設定")

st.subheader("ロゴ")
logos = sorted(path.as_posix() for path in Path("images").iterdir() if path.suffix.lower() in [".png", ".jpg", ".jpeg"])
columns = st.columns(len(logos))
for column, logo in zip(columns, logos):
    with column:
        st.image(logo, width=100)
        st.caption(logo_name(logo))

current = st.session_state.get("logo", "images/logo_nikukyu.png")
st.radio(
    "使うロゴ",
    logos,
    index=logos.index(current) if current in logos else 0,
    format_func=logo_name,
    horizontal=True,
    key="logo_choice",
    on_change=choose_logo,
)
st.caption("images フォルダに画像（PNG・JPG）を入れると、ここで選べるようになります。")

st.subheader("色")
colors = list(THEMES)
columns = st.columns(len(colors))
for column, color in zip(columns, colors):
    with column:
        st.markdown(f'<span style="color:{THEMES[color]["primaryColor"]}; font-size:2em;">●</span>', unsafe_allow_html=True)
        st.caption(color)

current_color = st.session_state.get("color", "緑")
st.radio(
    "使う色",
    colors,
    index=colors.index(current_color) if current_color in colors else 0,
    horizontal=True,
    key="color_choice",
    on_change=choose_color,
)