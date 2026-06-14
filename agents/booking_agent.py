import re
from datetime import datetime, timedelta

from skills.booking.booking_skill import check_availability


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

        if available:
            return (
                f"【練習室查詢結果】\n"
                f"你詢問的日期 {target_date} 有可預約時段：\n"
                + _format_availability(target_date, available)
            )

        suggestions = []
        for days_ahead in range(1, 4):
            next_date = (datetime.fromisoformat(target_date).date() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            next_results = check_availability(next_date)
            next_available = {room: slots for room, slots in next_results.items() if slots}
            if next_available:
                suggestions.append((next_date, next_available))

        if suggestions:
            text = [
                f"你詢問的日期 {target_date} 目前沒有可預約時段。",
                "以下是接下來 3 天內的可用時段建議：",
            ]
            for date_str, slots in suggestions:
                text.append(_format_availability(date_str, slots))
            return "\n".join(text)

        return (
            f"你詢問的日期 {target_date} 目前沒有可用時段，接下來 3 天內也都沒有發現可預約時段。"
            "\n請稍後再查或改用其他日期。"
        )
    except Exception as exc:
        return f"查詢時發生錯誤：{exc}\n請稍後再試。"
