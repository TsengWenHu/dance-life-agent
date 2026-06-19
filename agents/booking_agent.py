import re
import os
from datetime import datetime, timedelta

from openai import OpenAI
from skills.booking.booking_skill import check_availability
from prompts.booking_response_prompt import build_booking_response_prompt


def _parse_date(user_input: str) -> str | None:
    """Extract a target date from user input, supporting YYYY-MM-DD and common Chinese relative terms."""
    user_input = user_input.strip()

    # ISO date patterns like 2026-06-14, 2026/06/14, 2026.06.14
    m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", user_input)
    if m:
        try:
            year, month, day = map(int, m.groups())
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass

    today = datetime.now().date()
    keywords = {
        "今天": 0,
        "明天": 1,
        "後天": 2,
        "大後天": 3,
    }
    for key, offset in keywords.items():
        if key in user_input:
            return (today + timedelta(days=offset)).strftime("%Y-%m-%d")

    # fallback: look for 'X 日' or 'X 號' in the same month if no explicit date format
    day_match = re.search(r"(\d{1,2})\s*[日號]", user_input)
    if day_match:
        day = int(day_match.group(1))
        now = today
        try:
            candidate = datetime(now.year, now.month, day).date()
            if candidate >= today:
                return candidate.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def _format_availability(date: str, results: dict[str, list[str]]) -> str:
    lines = [f"{date} 可預約時段："]
    for room, slots in sorted(results.items()):
        if slots:
            lines.append(f"- {room}: {', '.join(slots)}")
    return "\n".join(lines)


def mock_response(user_input: str) -> str:
    target_date = _parse_date(user_input)
    if target_date is None:
        return (
            "請提供欲查詢的日期，格式例如 2026-06-14，或使用「明天」「後天」等詞。"
        )

    try:
        today = datetime.now().date()
        if datetime.fromisoformat(target_date).date() < today:
            return "請提供今天或之後的日期，才能查詢可預約時段。"

        results = check_availability(target_date)
        available = {room: slots for room, slots in results.items() if slots}

        suggestions = []
        for days_ahead in range(1, 4):
            next_date = (datetime.fromisoformat(target_date).date() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            next_results = check_availability(next_date)
            next_available = {room: slots for room, slots in next_results.items() if slots}
            if next_available:
                suggestions.append((next_date, next_available))

        if not available and not suggestions:
            return (
                f"你詢問的日期 {target_date} 目前沒有可用時段，接下來 3 天內也都沒有發現可預約時段。"
                "\n請稍後再查或改用其他日期。"
            )

        # 使用 LLM 產生更友善、易讀的結果回應
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        openai_model = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
        if openai_api_key:
            try:
                client = OpenAI(api_key=openai_api_key)
                prompt = build_booking_response_prompt(user_input, target_date, available, suggestions)
                resp = client.responses.create(
                    model=openai_model,
                    input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
                    text={"format": {"type": "text"}, "verbosity": "medium"},
                    reasoning={"effort": "medium", "summary": "auto"},
                    store=False,
                )

                outputs = getattr(resp, "output", None) or resp.get("output", [])
                texts = []
                for out in outputs:
                    contents = getattr(out, "content", None) if hasattr(out, "content") else out.get("content", [])
                    if not contents:
                        continue
                    for c in contents:
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

        # fallback to plain formatted response
        if available:
            text = [
                f"【練習室查詢結果】\n你詢問的日期 {target_date} 有可預約時段：",
                _format_availability(target_date, available),
                "\n📍 官網預約連結：https://www.practice-everything-dm.com\n你可以直接在官網選擇房間與時段進行預約。",
            ]
            if suggestions:
                text.append("\n以下是接下來 3 天內的可用時段建議：")
                for date_str, slots in suggestions:
                    text.append(_format_availability(date_str, slots))
            return "\n".join(text)

        return (
            f"你詢問的日期 {target_date} 目前沒有可預約時段。\n"
            "以下是接下來 3 天內的可用時段建議：\n"
            + "\n\n".join(_format_availability(date_str, slots) for date_str, slots in suggestions)
            + "\n\n📍 官網預約連結：https://www.practice-everything-dm.com"
        )
    except Exception as exc:
        return f"查詢時發生錯誤：{exc}\n請稍後再試。"


def get_availability(target_date: str, duration_hours: int = 1, location: str = None):
    """
    公開函式：取得指定日期的可用時段（只回傳有可用時段的房間）

    回傳： (available: dict[room -> list[str]], suggestions: list[(date, dict)])
    """
    try:
        results = check_availability(target_date, duration_hours=duration_hours, location=location)
        available = {room: slots for room, slots in results.items() if slots}

        suggestions = []
        for days_ahead in range(1, 4):
            next_date = (datetime.fromisoformat(target_date).date() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            next_results = check_availability(next_date, duration_hours=duration_hours, location=location)
            next_available = {room: slots for room, slots in next_results.items() if slots}
            if next_available:
                suggestions.append((next_date, next_available))

        return available, suggestions
    except Exception as exc:
        raise


def merge_contiguous_slots(slots: list[str], step_minutes: int = 30) -> list[str]:
    """
    將連續的可預約時段（例如 '07:00','07:30','08:00'）合併為區間文字表示。
    回傳例如 ['07:00-08:30', '10:00']。

    注意：此函式假設輸入的 slots 全部為可預約時段，不會檢查不可預約時段。
    """
    if not slots:
        return []

    def to_minutes(t: str) -> int:
        h, m = t.split(":")
        return int(h) * 60 + int(m)

    def to_time_str(minutes: int) -> str:
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"

    minutes = sorted(to_minutes(s) for s in slots)
    ranges = []
    start = minutes[0]
    prev = minutes[0]

    for cur in minutes[1:]:
        if cur - prev <= step_minutes:
            # contiguous or adjacent (<= step) -> extend
            prev = cur
            continue
        else:
            # close current range: end is prev + step_minutes
            end = prev + step_minutes
            if start == prev:
                ranges.append(to_time_str(start))
            else:
                ranges.append(f"{to_time_str(start)}-{to_time_str(end)}")
            start = cur
            prev = cur

    # finalize last range
    end = prev + step_minutes
    if start == prev:
        ranges.append(to_time_str(start))
    else:
        ranges.append(f"{to_time_str(start)}-{to_time_str(end)}")

    return ranges
