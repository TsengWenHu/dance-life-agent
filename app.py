import streamlit as st
from dotenv import load_dotenv
import tempfile
from typing import List, Dict

from agents import booking_agent
from i18n import (
    t,
    get_booking_keywords,
    detect_input_language,
    ui_language_options,
)

# load local env file if present (.env)
load_dotenv(".env")

from graph import run_graph


if "ui_language" not in st.session_state:
    st.session_state["ui_language"] = "zh"

# Streamlit 會先更新 widget key，再跑整支 script；先吃 selector 值可讓標題即時切換語言
effective_ui_language = st.session_state.get("ui_language_selector", st.session_state["ui_language"])
st.session_state["ui_language"] = effective_ui_language

st.set_page_config(page_title=t(st.session_state["ui_language"], "page_title"), page_icon="💃", layout="wide")

header_title = t(st.session_state["ui_language"], "header_title")

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
    <p class="neon-title">__HEADER_TITLE__</p>
    <hr class="neon-divider">
</div>
""".replace("__HEADER_TITLE__", header_title), unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state["history"] = []
if "uploaded_video_path" not in st.session_state:
    st.session_state["uploaded_video_path"] = None

lang_col_l, lang_col_r = st.columns([0.82, 0.18])
with lang_col_r:
    selected_language = st.selectbox(
        t(st.session_state["ui_language"], "language_label"),
        options=ui_language_options(),
        index=ui_language_options().index(st.session_state["ui_language"]),
        format_func=lambda code: t(st.session_state["ui_language"], f"language_option_{code}"),
        key="ui_language_selector",
        label_visibility="collapsed",
    )
    if selected_language != st.session_state["ui_language"]:
        st.session_state["ui_language"] = selected_language
        st.rerun()

ui_lang = st.session_state["ui_language"]

with st.sidebar:
    st.header(t(ui_lang, "sidebar_intro_title"))
    st.markdown(t(ui_lang, "sidebar_b1"))
    st.markdown(t(ui_lang, "sidebar_b2"))
    st.markdown(t(ui_lang, "sidebar_b3"))
    st.markdown("")
    
    # 檔案上傳區
    uploaded_file = st.file_uploader(
        t(ui_lang, "upload_label"),
        type=["mp4", "mov", "mkv", "avi", "flv"],
        help=t(ui_lang, "upload_help")
    )
    
    if uploaded_file is not None:
        # 儲存上傳的檔案到暫存資料夾
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            st.session_state["uploaded_video_path"] = tmp_file.name
        st.success(t(ui_lang, "upload_success", filename=uploaded_file.name))
        st.caption(t(ui_lang, "upload_size", size_mb=uploaded_file.size / (1024 * 1024)))
    else:
        st.session_state["uploaded_video_path"] = None
        st.info(t(ui_lang, "upload_hint"))

# 主聊天區
user_input = st.chat_input(t(ui_lang, "chat_placeholder"))
if user_input:
    # 立即顯示使用者訊息（避免等待 LLM 回應才看到）
    st.session_state["history"].append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # 若是練舞室查詢，嘗試顯示分段時段表格（早上/下午/晚上）
    booking_keywords = get_booking_keywords()
    booking_table_data = None
    lowered_user_input = user_input.lower()
    if any(k in lowered_user_input for k in booking_keywords):
        try:
            with st.status(t(ui_lang, "booking_status_title"), expanded=True) as status_container:
                target_date = booking_agent._parse_date(user_input)
                if target_date:
                    st.write(t(ui_lang, "booking_query_date", date=target_date))
                    st.write(t(ui_lang, "booking_fetching"))
                    
                    available, suggestions = booking_agent.get_availability(target_date)
                    st.write(t(ui_lang, "booking_found_rooms", count=len(available)))

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
                            t(ui_lang, "table_morning"): ", ".join(morning) if morning else "-",
                            t(ui_lang, "table_afternoon"): ", ".join(afternoon) if afternoon else "-",
                            t(ui_lang, "table_evening"): ", ".join(night) if night else "-",
                        }

                    table_rows = []
                    for room, slots in sorted(available.items()):
                        merged = booking_agent.merge_contiguous_slots(slots)
                        cats = categorize_merged(merged)
                        row = {
                            t(ui_lang, "table_room"): room,
                            t(ui_lang, "table_morning"): cats[t(ui_lang, "table_morning")],
                            t(ui_lang, "table_afternoon"): cats[t(ui_lang, "table_afternoon")],
                            t(ui_lang, "table_evening"): cats[t(ui_lang, "table_evening")],
                        }
                        table_rows.append(row)

                    if table_rows:
                        st.write(t(ui_lang, "booking_formatting"))
                        st.markdown(t(ui_lang, "booking_table_title"))
                        st.table(table_rows)
                    
                    status_container.update(label=t(ui_lang, "booking_done"), state="complete")
        except Exception as e:
            st.error(t(ui_lang, "booking_failed", error=e))

    # 取得目前的影片路徑（若有），再呼叫後端圖譜進行完整回應
    current_video_path = st.session_state.get("uploaded_video_path")
    input_language = detect_input_language(user_input, fallback=ui_lang)
    with st.status(t(ui_lang, "analyzing_title"), expanded=False) as status:
        st.write(t(ui_lang, "analyzing_intent"))
        response = run_graph(
            user_input,
            video_path=current_video_path,
            input_language=input_language,
        )
        status.update(label=t(ui_lang, "analyzing_done"), state="complete")

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
            f"[{t(ui_lang, 'official_link_text')}](https://www.practice-everything-dm.com)"
        )
        st.chat_message("assistant").write(response_text, unsafe_allow_html=False)
