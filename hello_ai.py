import anthropic
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

st.title("AIのテスト")

if st.button("AIにあいさつする"):
    response = client.beta.messages.create(
        model="claude-opus-5-5",
        max_tokens=1000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": "こんにちは"}],
    )
    for block in response.content:
        if block.type == "text":
            st.write(block.text)