import streamlit as st
from dotenv import load_dotenv
import os
import tempfile
from typing import List, Dict

from agents import booking_agent
from skills.booking.booking_skill import check_availability

# load local env file if present (.env)
load_dotenv(".env")

from graph import run_graph


st.set_page_config(page_title="舞蹈練習助理", page_icon="💃", layout="wide")

st.markdown("""
<style>
/* 全域霓虹風格 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans TC', sans-serif;
}

/* 隱藏預設 header/footer */
#MainMenu, footer, header { visibility: hidden; }

/* 主背景 */
.stApp {
    background: linear-gradient(135deg, #0A0A0A 0%, #0D0A1A 50%, #0A0A0A 100%);
}

/* 頂部標題區 */
.neon-header {
    text-align: center;
    padding: 2rem 1rem 1rem;
}
.neon-title {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(90deg, #B44FE8, #00F5D4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-shadow: none;
    margin: 0;
    letter-spacing: 2px;
}
.neon-subtitle {
    color: #888;
    font-size: 0.9rem;
    margin-top: 0.5rem;
    letter-spacing: 1px;
}
.neon-divider {
    height: 2px;
    background: linear-gradient(90deg, transparent, #B44FE8, #00F5D4, transparent);
    border: none;
    margin: 1rem 0;
    width: 100%;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0D0D1A !important;
    border-right: 1px solid #B44FE820;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #B44FE8 !important;
}
[data-testid="stSidebar"] .stMarkdown p {
    color: #CCC;
    font-size: 0.88rem;
}

/* 上傳元件 */
[data-testid="stFileUploader"] {
    border: 1px dashed #B44FE860 !important;
    border-radius: 12px !important;
    background: #141424 !important;
    padding: 0.5rem;
}

/* 成功/資訊訊息 */
[data-testid="stAlert"] {
    border-radius: 10px !important;
}

/* Chat input */
[data-testid="stChatInput"] {
    padding: 1rem 2rem !important;
    margin: 1rem 2rem 0 2rem !important;
}
[data-testid="stChatInput"] textarea {
    background: #141424 !important;
    border: 1px solid #B44FE840 !important;
    border-radius: 12px !important;
    color: #FFF !important;
    transition: border 0.3s;
    padding: 1rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #B44FE8 !important;
    box-shadow: 0 0 12px #B44FE840 !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    border-radius: 14px !important;
    margin-bottom: 0.5rem !important;
}
[data-testid="stChatMessage"][data-role="user"] {
    background: #1A0D2E !important;
    border: 1px solid #B44FE830 !important;
}
[data-testid="stChatMessage"][data-role="assistant"] {
    background: #0A1A1A !important;
    border: 1px solid #00F5D430 !important;
}

/* Spinner */
[data-testid="stSpinner"] {
    color: #00F5D4 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0A0A0A; }
::-webkit-scrollbar-thumb { background: #B44FE860; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #B44FE8; }
</style>

<div class="neon-header">
    <p class="neon-title">💃 你的跳舞好夥伴 💃</p>
    <hr class="neon-divider">
</div>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state["history"] = []
if "uploaded_video_path" not in st.session_state:
    st.session_state["uploaded_video_path"] = None

with st.sidebar:
    st.header("使用說明")
    st.markdown("### 快速功能介紹")
    st.markdown("- 舞動疑難雜症？問我！🎤")
    st.markdown("- 上傳影片，提供建議＋給練習計畫🎯")
    st.markdown("- 查練舞室空檔，快速找到場地🕒")
    st.markdown("")
    st.markdown("- 輸入範例：練習室查詢「明天下午有哪些練習室空著？」")
    st.markdown("")
    
    # 檔案上傳區
    uploaded_file = st.file_uploader(
        "上傳練習影片",
        type=["mp4", "mov", "mkv", "avi", "flv"],
        help="支援 mp4, mov, mkv, avi, flv"
    )
    
    if uploaded_file is not None:
        # 儲存上傳的檔案到暫存資料夾
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            st.session_state["uploaded_video_path"] = tmp_file.name
        st.success(f"✅ 已上傳: {uploaded_file.name}")
        st.caption(f"檔案大小: {uploaded_file.size / (1024*1024):.2f} MB")
    else:
        st.session_state["uploaded_video_path"] = None
        st.info("📹 可以上傳影片給我分析喔～")

# 主聊天區
user_input = st.chat_input("請輸入問題...")
if user_input:
    # 立即顯示使用者訊息（避免等待 LLM 回應才看到）
    st.session_state["history"].append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # 若是練舞室查詢，嘗試顯示分段時段表格（早上/下午/晚上）
    booking_keywords = ["練習室", "練舞室", "房間", "預約", "可預約", "場地", "空檔"]
    booking_table_data = None
    if any(k in user_input for k in booking_keywords):
        try:
            with st.status("🔍 正在查詢練舞室資料...", expanded=True) as status_container:
                target_date = booking_agent._parse_date(user_input)
                if target_date:
                    st.write(f"📅 查詢日期: {target_date}")
                    st.write("🔄 正在爬取練舞室資訊...")
                    
                    available, suggestions = booking_agent.get_availability(target_date)
                    st.write(f"✅ 找到 {len(available)} 個房間")

                    # 將可用時段合併連續區間，再依照早/中/晚分類顯示
                    def categorize_merged(merged_ranges: List[str]) -> Dict[str, str]:
                        morning = []
                        afternoon = []
                        night = []
                        for r in merged_ranges:
                            start = r.split("-")[0]
                            try:
                                h = int(start.split(":")[0])
                            except Exception:
                                continue
                            if h < 12:
                                morning.append(r)
                            elif 12 <= h < 18:
                                afternoon.append(r)
                            else:
                                night.append(r)
                        return {
                            "早上": ", ".join(morning) if morning else "-",
                            "下午": ", ".join(afternoon) if afternoon else "-",
                            "晚上": ", ".join(night) if night else "-",
                        }

                    table_rows = []
                    for room, slots in sorted(available.items()):
                        merged = booking_agent.merge_contiguous_slots(slots)
                        cats = categorize_merged(merged)
                        row = {"練舞室": room, "早上": cats["早上"], "下午": cats["下午"], "晚上": cats["晚上"]}
                        table_rows.append(row)

                    if table_rows:
                        st.write("⏱️ 格式化時段...")
                        st.markdown("**可預約時段（已合併區間）**")
                        st.table(table_rows)
                    
                    status_container.update(label="✨ 查詢完成", state="complete")
        except Exception as e:
            st.error(f"查詢失敗: {e}")

    # 取得目前的影片路徑（若有），再呼叫後端圖譜進行完整回應
    current_video_path = st.session_state.get("uploaded_video_path")
    with st.status("🤔 正在分析您的問題...", expanded=False) as status:
        st.write("⚡ 判斷意圖中...")
        response = run_graph(user_input, video_path=current_video_path)
        status.update(label="✨ 回應完成", state="complete")

    # 若有表格資料，也保存到歷史（用特殊標記識別）
    st.session_state["history"].append({"role": "assistant", "content": response})

# 顯示聊天歷史
for message in st.session_state["history"]:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        # 將官網連結轉成 markdown 可點擊超連結
        response_text = message["content"]
        response_text = response_text.replace(
            "https://www.practice-everything-dm.com",
            "[官網預約連結](https://www.practice-everything-dm.com)"
        )
        st.chat_message("assistant").write(response_text, unsafe_allow_html=False)
