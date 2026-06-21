import re
from typing import Dict, List


UI_STRINGS: Dict[str, Dict[str, str]] = {
    "zh": {
        "page_title": "舞蹈練習助理",
        "header_title": "💃 你的跳舞好夥伴 💃",
        "sidebar_intro_title": "快速功能介紹",
        "sidebar_b1": "- 舞蹈疑難雜症？問我！🎤",
        "sidebar_b2": "- 上傳影片，提供建議＋給練習計畫🎯",
        "sidebar_b3": "- 查練舞室空檔，快速找到場地🕒（輸入範例：練習室查詢「明天下午有哪些練習室空著？」）",
        "upload_label": "上傳練習影片",
        "upload_help": "支援 mp4, mov, mkv, avi, flv",
        "upload_success": "✅ 已上傳: {filename}",
        "upload_size": "檔案大小: {size_mb:.2f} MB",
        "upload_hint": "📹 可以上傳影片給我分析喔～",
        "chat_placeholder": "請輸入問題...",
        "booking_status_title": "🔍 正在查詢練舞室資料...",
        "booking_query_date": "📅 查詢日期: {date}",
        "booking_fetching": "🔄 正在爬取練舞室資訊...",
        "booking_found_rooms": "✅ 找到 {count} 個房間",
        "booking_formatting": "⏱️ 格式化時段...",
        "booking_table_title": "**可預約時段（已合併區間）**",
        "booking_done": "✨ 查詢完成",
        "booking_failed": "查詢失敗: {error}",
        "analyzing_title": "🤔 正在分析您的問題...",
        "analyzing_intent": "⚡ 判斷意圖中...",
        "analyzing_done": "✨ 回應完成",
        "table_room": "練舞室",
        "table_morning": "早上",
        "table_afternoon": "下午",
        "table_evening": "晚上",
        "language_label": "語言",
        "language_option_zh": "中文",
        "language_option_en": "English",
        "official_link_text": "官網預約連結",
    },
    "en": {
        "page_title": "Dance Practice Assistant",
        "header_title": "💃 Your Dance Practice Partner 💃",
        "sidebar_intro_title": "Quick Features",
        "sidebar_b1": "- Dance questions? Ask me! 🎤",
        "sidebar_b2": "- Upload a video for suggestions + a practice plan 🎯",
        "sidebar_b3": "- Check studio availability quickly 🕒 (Example: \"Which practice rooms are available tomorrow afternoon?\")",
        "upload_label": "Upload practice video",
        "upload_help": "Supported: mp4, mov, mkv, avi, flv",
        "upload_success": "✅ Uploaded: {filename}",
        "upload_size": "File size: {size_mb:.2f} MB",
        "upload_hint": "📹 Upload a video for deeper analysis.",
        "chat_placeholder": "Type your question...",
        "booking_status_title": "🔍 Checking studio availability...",
        "booking_query_date": "📅 Target date: {date}",
        "booking_fetching": "🔄 Fetching studio slots...",
        "booking_found_rooms": "✅ Found {count} room(s)",
        "booking_formatting": "⏱️ Formatting time ranges...",
        "booking_table_title": "**Available time ranges (merged)**",
        "booking_done": "✨ Search completed",
        "booking_failed": "Search failed: {error}",
        "analyzing_title": "🤔 Analyzing your request...",
        "analyzing_intent": "⚡ Detecting intent...",
        "analyzing_done": "✨ Response ready",
        "table_room": "Studio",
        "table_morning": "Morning",
        "table_afternoon": "Afternoon",
        "table_evening": "Evening",
        "language_label": "Language",
        "language_option_zh": "中文",
        "language_option_en": "English",
        "official_link_text": "Official booking link",
    },
}


BOOKING_KEYWORDS: Dict[str, List[str]] = {
    "zh": ["練習室", "練舞室", "房間", "預約", "可預約", "場地", "空檔"],
    "en": [
        "practice room",
        "studio",
        "booking",
        "reserve",
        "reservation",
        "availability",
        "slot",
        "room",
    ],
}


def t(lang: str, key: str, **kwargs: object) -> str:
    language = lang if lang in UI_STRINGS else "zh"
    text = UI_STRINGS[language].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def get_booking_keywords() -> List[str]:
    return BOOKING_KEYWORDS["zh"] + BOOKING_KEYWORDS["en"]


def detect_input_language(text: str, fallback: str = "zh") -> str:
    content = (text or "").strip()
    if not content:
        return fallback if fallback in {"zh", "en"} else "zh"

    cjk_chars = re.findall(r"[\u4e00-\u9fff]", content)
    latin_chars = re.findall(r"[A-Za-z]", content)

    cjk_count = len(cjk_chars)
    latin_count = len(latin_chars)

    if cjk_count == 0 and latin_count == 0:
        return fallback if fallback in {"zh", "en"} else "zh"

    if cjk_count >= latin_count:
        return "zh"
    return "en"


def ui_language_options() -> List[str]:
    return ["zh", "en"]
