import os
from openai import OpenAI

from prompts.dance_prompt import build_dance_prompt


def analyze_dance(user_input: str) -> str:
    """
    使用 OpenAI Responses API 進行舞蹈分析。

    環境變數：`OPENAI_API_KEY`、`OPENAI_MODEL`（預設 gpt-5.4-mini）
    """
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")

        if not api_key:
            return mock_response_missing_api()

        client = OpenAI(api_key=api_key)

        prompt = build_dance_prompt(user_input)

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
                return "\n\n".join(texts)

        except Exception:
            pass

        # fallback: return full raw response string
        return str(resp)

    except Exception as e:
        return f"分析出錯：{str(e)}\n\n請檢查 OPENAI_API_KEY 與 OPENAI_MODEL 是否設定正確。"


def mock_response_missing_api() -> str:
    return (
        "【舞蹈分析 mock 回應】\n"
        "- OpenAI API Key 未設定\n"
        "- 請設定 OPENAI_API_KEY 與 OPENAI_MODEL 環境變數（例如 OPENAI_MODEL=gpt-5.4-mini）"
    )
