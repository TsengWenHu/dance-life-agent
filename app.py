import streamlit as st
from dotenv import load_dotenv
import os

# load local env file if present (.env)
load_dotenv(".env")

from graph import run_graph


st.set_page_config(page_title="舞蹈練習助理", page_icon="💃")
st.title("舞蹈練習助理 AI Agent Phase 1")
st.write(
    "這個 demo 使用 LangGraph 進行意圖路由，並回傳舞蹈分析或練習室預約查詢結果。"
)

if "history" not in st.session_state:
    st.session_state["history"] = []

with st.sidebar:
    st.header("使用說明")
    st.markdown("- 輸入舞蹈動作問題，例如「我的 body roll 重心往前」")
    st.markdown("- 輸入練習室查詢，例如「明天下午有哪些練習室空著？」")
    st.markdown("- 練習室查詢會使用實際可用時段查詢，不會自動預約")

user_input = st.chat_input("請輸入問題...")
if user_input:
    st.session_state["history"].append({"role": "user", "content": user_input})
    with st.spinner("正在判斷意圖..."):
        response = run_graph(user_input)
    st.session_state["history"].append({"role": "assistant", "content": response})

for message in st.session_state["history"]:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])
