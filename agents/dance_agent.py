import os
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

from prompts.dance_prompt import build_dance_prompt
from prompts.dance_no_video_prompt import build_dance_no_video_prompt


def analyze_dance(user_input: str, video_path: str | None = None, input_language: str = "zh") -> str:
    """
    使用 OpenAI Responses API 進行舞蹈分析。
    
    Args:
        user_input: 使用者的舞蹈問題或描述
        video_path: 可選，上傳的影片檔案路徑。若提供則進行量化評分；若 None 則只回答問題
    
    環境變數：`OPENAI_API_KEY`、`OPENAI_MODEL`（預設 gpt-5.4-mini）
    """
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")

        if not api_key or OpenAI is None:
            return mock_response_missing_api(user_input=user_input, video_path=video_path)

        client = OpenAI(api_key=api_key)

        # 根據是否有影片，選用不同的 prompt
        if video_path:
            prompt = build_dance_prompt(user_input, language=input_language)
        else:
            prompt = build_dance_no_video_prompt(user_input, language=input_language)

        resp = client.responses.create(
            model=model,
            input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            text={"format": {"type": "text"}, "verbosity": "medium"},
            reasoning={"effort": "medium", "summary": "auto"},
            store=False,
        )

        # 嘗試從回應中抽取主要文字輸出：遍歷 output 裡的每一個 item 和其 content
        try:
            outputs = getattr(resp, "output", None) or resp.get("output", [])
            texts = []
            for out in outputs:
                contents = getattr(out, "content", None) if hasattr(out, "content") else out.get("content", [])
                if not contents:
                    continue
                for c in contents:
                    # c 可能是 dict 或物件
                    if isinstance(c, dict):
                        t = c.get("text")
                    else:
                        t = getattr(c, "text", None)
                    if t:
                        texts.append(t)

            if texts:
                response_text = "\n\n".join(texts)
                if input_language == "en" and _contains_cjk(response_text):
                    return _english_dance_fallback(user_input=user_input, video_path=video_path)
                return response_text

        except Exception:
            pass

        # fallback: return full raw response string
        fallback_text = str(resp)
        if input_language == "en" and _contains_cjk(fallback_text):
            return _english_dance_fallback(user_input=user_input, video_path=video_path)
        return fallback_text

    except Exception as e:
        return f"分析出錯：{str(e)}\n\n請檢查 OPENAI_API_KEY 與 OPENAI_MODEL 是否設定正確。"


def mock_response_missing_api(user_input: str, video_path: str | None = None) -> str:
    base = (
        "【舞蹈分析 mock 回應】\n"
        "- OpenAI API Key 未設定\n"
        "- 請設定 OPENAI_API_KEY 與 OPENAI_MODEL 環境變數（例如 OPENAI_MODEL=gpt-5.4-mini）"
    )

    if video_path is None:
        return (
            base +
            "\n- 目前尚未上傳影片。若要進一步提供完整舞蹈分析與改善建議，請上傳練習影片。"
        )

    return base


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _english_dance_fallback(user_input: str, video_path: str | None = None) -> str:
    if video_path:
        return (
            "### Dance Analysis Report\n\n"
            "#### 1. Overall Assessment\n"
            "Based on your description, I can give a preliminary analysis, but a video would allow a much more accurate evaluation.\n\n"
            "#### 2. Issue Diagnosis\n"
            "- The most likely technical gaps are groove consistency, center control, and body relaxation.\n"
            "- The movement may look unconnected or lack musical flow.\n\n"
            "#### 3. Category Scores\n"
            "- Stability: __/10\n"
            "- Tension: __/10\n"
            "- Musicality: __/10\n"
            "- Center Control: __/10\n"
            "- Move Completion: __/10\n"
            "- Flow / Transitions: __/10\n"
            "- Average: __/10\n\n"
            "#### 4. This Week's Improvement Plan\n"
            "1. Groove isolation drill\n"
            "   - Purpose: Build steadier rhythm and body control.\n"
            "   - Method: Practice chest, rib, and hip isolation to a slow beat.\n"
            "   - Frequency / Duration: 10 minutes a day.\n\n"
            "2. Musicality layering drill\n"
            "   - Purpose: Improve timing and phrase awareness.\n"
            "   - Method: Repeat one short phrase and match accents more clearly.\n"
            "   - Frequency / Duration: 3 rounds per session.\n"
        )

    return (
        "### 1. Diagnosis\n"
        "- Your question is in English, so I am answering in English.\n"
        "- The most likely technical blind spot is groove consistency or body control.\n\n"
        "### 2. Improvement Suggestions\n"
        "1. Groove pulse drill\n"
        "   - Purpose: Build steadier timing and relaxed movement.\n"
        "   - Method: Move on the beat with small body isolations.\n"
        "   - Recommended frequency: 5 to 10 minutes daily.\n\n"
        "2. Body control drill\n"
        "   - Purpose: Improve center control and cleaner transitions.\n"
        "   - Method: Practice slow motion reps and hold each position.\n"
        "   - Recommended frequency: 3 sets per session.\n\n"
        "### 3. Video Reminder\n"
        "If you want a more accurate assessment, please upload a practice video."
    )
