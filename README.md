# Dance Practice Agent

這是一個用於展示多 agent 與 LangGraph 路由的 Streamlit Demo 專案。使用 OpenAI 官方 API 與 LangGraph 實現意圖路由，提供舞蹈分析與練習室預約查詢功能。

## 核心功能

### 1. 練習室空位查詢
- 查詢指定日期的練習室可預約時段
- 支援中文相對日期（「明天」、「後天」等）
- 返回各房間的可用時間清單
- 當詢問的日期無可用時段時，自動建議近 3 天的替代方案

### 2. 舞蹈分析（支援影片檢查機制）
#### 無上傳影片時
- 系統只提供**技術建議**與**問題回答**
- **不進行量化評分**
- 例如：「如何改善 body roll 的重心」→ 提供改善技巧

#### 上傳影片後
- 系統進行**完整量化評分**
- 包含：穩定度、張力、音樂性、重心控制、動作完成度、Flow/連接性
- 提供詳細分析報告與本週改善建議

## 快速使用

### 環境設定

1. 建立虛擬環境：
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 複製 `.env.example` 為 `.env` 並填入 API 金鑰：
```bash
cp .env.example .env
```

編輯 `.env` 並填入：
- `OPENAI_API_KEY=your_openai_key`
- `OPENAI_MODEL=gpt-4o-mini` (或其他 OpenAI 模型)
- `PE_EMAIL=your_pe_email` (可選，用於練習室查詢)
- `PE_PASSWORD=your_pe_password` (可選，用於練習室查詢)

3. 執行 Streamlit 應用：
```bash
streamlit run app.py
```

## 使用方式

### Streamlit UI
- 在側欄上傳練習影片（可選）
- 在下方聊天框輸入問題
- 根據是否上傳影片，系統會提供不同模式的回應

### 舞蹈問題範例
- **無影片時**：「我的 body roll 重心往前，應該怎麼改？」
- **有影片時**：「請分析我的舞蹈動作」→ 獲得完整評分報告

### 練習室查詢範例
- 「明天有哪些練習室空著？」
- 「2026-06-20 下午有沒有 Z01 房間可以預約？」
- 「後天上午的可用時段」

## 專案結構

```
dance-life-agent/
├── app.py                          # Streamlit 入口，包含檔案上傳功能
├── graph.py                        # LangGraph 路由邏輯 (StateGraph)
├── agents/
│   ├── dance_agent.py             # 舞蹈分析 agent（支援有無影片分流）
│   └── booking_agent.py           # 練習室查詢 agent
├── prompts/
│   ├── dance_prompt.py            # 有影片時的舞蹈分析 prompt
│   ├── dance_no_video_prompt.py   # 無影片時的技術問答 prompt
│   └── router_prompt.py           # 意圖分類 prompt
├── skills/
│   ├── booking/                   # 練習室查詢工具
│   │   └── booking_skill.py       # 實際查詢 API
│   └── dance_teacher_compare/     # 舞蹈分析相關工具
├── tests/
│   └── test_dance_with_without_video.py  # 舞蹈分析測試
├── requirements.txt               # Python 依賴
├── .env.example                  # 環境變數範本
└── README.md                     # 本檔案
```

## 技術架構

### LangGraph 路由流程
1. **Router Node** 使用 OpenAI API 判斷使用者意圖
2. **意圖分類**：
   - `dance_analysis` → 舞蹈分析 agent
   - `room_booking` → 練習室查詢 agent
3. **Agent 執行**：根據分類執行對應邏輯
4. **回應返回**：Streamlit UI 展示結果

### 舞蹈分析分流邏輯
- **有 `video_path`**：使用 `dance_prompt.py` 進行量化評分
- **無 `video_path`**：使用 `dance_no_video_prompt.py` 進行純技術問答

## 測試

執行舞蹈分析測試（無影片 vs 有影片）：

```bash
cd tests
python test_dance_with_without_video.py
```

預期結果：
- ✅ 無影片模式回應中不包含分數
- ✅ 有影片模式包含完整分析內容

## 環境變數說明

| 變數 | 必需 | 說明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | OpenAI API 金鑰 |
| `OPENAI_MODEL` | ✅ | 使用的 OpenAI 模型（如 `gpt-4o-mini`） |
| `PE_EMAIL` | ❌ | Practice Everything 帳號 email（用於查詢） |
| `PE_PASSWORD` | ❌ | Practice Everything 帳號密碼（用於查詢） |

## 使用 Git 提交

### 安全提交（確保 `.env` 不被上傳）

```bash
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your_repo_url>
git push -u origin main
```

### 驗證 `.env` 未被追蹤

```bash
git check-ignore -v .env
```

應該輸出：`.env`（表示被正確忽略）

## 後續開發方向

### Phase 3 計劃
- [ ] 美化 Streamlit 介面（自訂主題與佈局）
- [ ] 支援影片多媒體上傳到雲端（Google Drive）
- [ ] 集成 Hermes agent 架構以支持多通道（WhatsApp、Slack 等）
- [ ] 新增預約確認流程（不自動預約，需使用者確認）
- [ ] 加入錄音自動上傳功能

## 注意事項

- 影片檔案在 Streamlit 中的暫存位置不會被 commit（`.gitignore` 包含 `*.mp4` 等）
- 無影片模式下的回應**不包含量化分數**，僅提供技術建議
- 練習室查詢功能依賴外部 PE 網站的可用性
- OpenAI API 調用會產生費用，請留意使用量

## 授權

MIT License（可根據需要調整）
