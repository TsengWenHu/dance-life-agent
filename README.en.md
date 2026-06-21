# Dance Practice Agent

Chinese version: [README.md](README.md)

This is a Streamlit demo project that showcases multi-agent routing with LangGraph and the OpenAI API. It provides dance analysis and dance studio booking availability support.

## Demo

- Live Demo: (add your deployed app URL)
- Demo Video: (add your YouTube/Loom URL)
- Recommended 60-90s walkthrough:
   1. Switch UI between Chinese and English
   2. Show input-language-aware responses (EN in -> EN out, ZH in -> ZH out)
   3. Show booking query with tomorrow / next Monday / YYYY-MM-DD

## Key Outcomes

- Delivered a portfolio-ready AI assistant with LangGraph routing and Streamlit UX
- Implemented bilingual UX: switchable UI language plus input-language-aware model responses
- Built practical booking flow: Chinese and English date parsing with readable slot summaries
- Added maintainability baseline via tests for language detection and date parsing

## Tech Decisions

- Why LangGraph: explicit separation between intent classification and task execution
- Why Streamlit: fastest path to an interactive demo recruiters can run immediately
- Why i18n.py: centralized UI text and language detection instead of scattered literals
- Why output-language safeguards: mitigates occasional model language drift and keeps response language aligned with user input

## Portfolio Highlights

- Bilingual Streamlit UI (Traditional Chinese / English)
- Input-language-aware replies: Chinese input gets Chinese output, English input gets English output
- LangGraph intent routing: dance_analysis / room_booking
- Studio availability query with both Chinese and English date expressions

## Core Features

### 1. Studio Availability Query
- Query available dance studio time slots for a target date
- Supports Chinese relative dates (for example, today, tomorrow, day after tomorrow)
- Returns available slots by room
- If the target date has no availability, suggests alternatives in the next 3 days

### 2. Dance Analysis (Video-Aware Flow)
#### Without an uploaded video
- The system provides technique suggestions and question answering
- No quantitative scoring is returned
- Example: "How can I improve my body roll center control?"

#### With an uploaded video
- The system returns a full quantitative analysis
- Includes stability, tension, musicality, center control, move completion, and flow/transitions
- Provides a detailed report and a weekly improvement plan

## Quick Start

### Environment Setup

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy .env.example to .env:

```bash
cp .env.example .env
```

Set values in .env:
- OPENAI_API_KEY=your_openai_key
- OPENAI_MODEL=gpt-5.4-mini (or another model supported by OpenAI Responses)
- PE_EMAIL=your_pe_email (optional, for booking query)
- PE_PASSWORD=your_pe_password (optional, for booking query)

3. Run the Streamlit app:

```bash
streamlit run app.py
```

## Usage

### Streamlit UI
- Optionally upload a practice video in the sidebar
- Enter your question in the chat input box
- The response mode changes based on whether a video is uploaded

### Dance Question Examples
- Without video: "How can I improve my body roll center control?"
- With video: "Please analyze my dance movement"

### Studio Query Examples
- "What studios are available tomorrow?"
- "Is Z01 available on 2026-06-20 afternoon?"
- "Any available slots for the day after tomorrow morning?"
- "Any practice room available tomorrow afternoon?"
- "Can I reserve a studio on June 20?"

### Bilingual Behavior
- UI language can be switched at the top-right corner (Traditional Chinese / English)
- LLM response language follows user input language and is not forced to match UI language
- English date expressions supported: tomorrow, day after tomorrow, next Monday, June 20, YYYY-MM-DD

## Project Structure

```text
dance-life-agent/
|-- app.py                          # Streamlit entry point with upload and chat UI
|-- i18n.py                         # UI text dictionary and input language detection
|-- graph.py                        # LangGraph routing logic
|-- agents/
|   |-- dance_agent.py              # Dance analysis agent (with/without video)
|   `-- booking_agent.py            # Studio booking query agent
|-- prompts/
|   |-- dance_prompt.py             # Prompt for video-based dance analysis
|   |-- dance_no_video_prompt.py    # Prompt for no-video dance guidance
|   `-- router_prompt.py            # Intent classifier prompt
|-- skills/
|   |-- booking/
|   |   `-- booking_skill.py        # Booking query implementation
|   `-- dance_teacher_compare/      # Dance-analysis related tools
|-- tests/
|   |-- test_dance_with_without_video.py
|   `-- test_i18n_booking_language_unittest.py
|-- requirements.txt
|-- .env.example
`-- README.md
```

## Architecture

### LangGraph Routing Flow
1. Router node classifies user intent via OpenAI API
2. Intent label:
   - dance_analysis -> dance agent
   - room_booking -> booking agent
3. Corresponding agent executes logic
4. Response is returned to Streamlit UI

### Dance Analysis Split Logic
- With video_path: use dance_prompt.py for quantitative scoring
- Without video_path: use dance_no_video_prompt.py for technical guidance only

## Testing

Run dance behavior tests (with vs without video):

```bash
python3 tests/test_dance_with_without_video.py
```

Run i18n and date parsing tests:

```bash
python3 -m unittest -q tests/test_i18n_booking_language_unittest.py
```

Expected:
- No-video mode should not include score tables
- Video mode should return structured analysis content

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| OPENAI_API_KEY | Yes | OpenAI API key |
| OPENAI_MODEL | Yes | OpenAI model name (for example, gpt-5.4-mini) |


## Git Submission

### Safe Commit

```bash
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <your_repo_url>
git push -u origin main
```

### Verify .env is ignored

```bash
git check-ignore -v .env
```

Expected output includes .env, which means it is ignored correctly.

## Roadmap

### Phase 3 Plan
- Polish Streamlit visual design and layout
- Support cloud media upload flow (for example, Google Drive)
- Integrate Hermes-style multi-channel capability (for example, WhatsApp, Slack)
- Add booking confirmation flow (no automatic booking)
- Add recording upload support

## Notes

- Uploaded video temp files are excluded from git via .gitignore
- No-video mode returns guidance only, without quantitative scoring
- Booking query depends on the external PE service availability
- OpenAI API usage may incur cost

## License

MIT License. See LICENSE for details.
