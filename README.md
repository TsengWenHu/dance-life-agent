# Dance Practice Agent

這是一個用於展示多 agent 與 LangGraph 路由的 Streamlit Demo 專案。

## Phase 1

- 使用 AzureChatOpenAI 進行意圖判斷
- `dance_analysis` 與 `room_booking` 走不同 mock agent
- Streamlit chat 介面展示對話

## 快速使用

1. 建立虛擬環境：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. 複製 `.env.example` 為 `.env` 並填入 Azure 與 PE 資訊。
3. 執行 app：
   ```bash
   streamlit run app.py
   ```

## 專案結構

- `app.py`：Streamlit 入口
- `graph.py`：LangGraph 意圖路由與 mock agent 路徑
- `agents/`：agent mock 回應
- `prompts/`：router prompt 與 future dance prompt
- `tools/`：placeholder 工具封裝
- `skills/`：直接複用的 booking 與 dance prompt 資料夾
