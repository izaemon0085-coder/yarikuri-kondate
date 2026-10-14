import streamlit as st

st.title("買い物の記録")
st.write("ここで、レシートの読み取りや、買い物の記録をします。")

receipt = st.file_uploader("レシートの写真（JPG・PNG）", type=["jpg", "jpeg", "png"])
if receipt is not None:
    st.image(receipt, caption=receipt.name, width=300)



