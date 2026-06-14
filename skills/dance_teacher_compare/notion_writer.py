from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from dotenv import load_dotenv


NOTION_VERSION = "2022-06-28"


class NotionConfigError(RuntimeError):
    pass


class ReportJsonError(RuntimeError):
    pass


def extract_report_json(report: str) -> dict[str, Any]:
    matches = re.findall(r"```json\s*(\{.*?\})\s*```", report, flags=re.DOTALL)
    if not matches:
        raise ReportJsonError("Gemini 報告中找不到 fenced JSON 摘要。")

    raw_json = matches[-1]
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ReportJsonError(f"Gemini JSON 摘要無法解析：{exc}") from exc

    if not isinstance(parsed, dict):
        raise ReportJsonError("Gemini JSON 摘要不是 object。")
    return parsed


def notion_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def text_property(value: str) -> dict[str, list[dict[str, dict[str, str]]]]:
    return {"rich_text": [{"text": {"content": value[:2000]}}]} if value else {"rich_text": []}


def title_property(value: str) -> dict[str, list[dict[str, dict[str, str]]]]:
    return {"title": [{"text": {"content": value[:2000]}}]}


def select_property(value: str) -> dict[str, dict[str, str]]:
    return {"select": {"name": value}}


def url_property(value: str) -> dict[str, str | None]:
    return {"url": value or None}


def format_practice_prescription(items: list[dict[str, Any]]) -> str:
    lines = []
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. {item.get('name', '')}")
        for key, label in [
            ("purpose", "目的"),
            ("method", "做法"),
            ("duration", "次數 / 時長"),
            ("check_standard", "檢查標準"),
        ]:
            value = item.get(key)
            if value:
                lines.append(f"- {label}：{value}")
    return "\n".join(lines)


def build_notion_properties(summary: dict[str, Any], report: str) -> dict[str, Any]:
    source_videos = summary.get("source_videos", {})
    teacher_video = source_videos.get("teacher_video", {})
    student_video = source_videos.get("student_video", {})
    practice_prescription = summary.get("practice_prescription", [])
    next_check_focus = summary.get("next_check_focus", [])
    weakness_tags = summary.get("weakness_tags", [])

    title = f"{summary.get('date', '')} {summary.get('dance_style', '')} {summary.get('mode', '老師對比')}".strip()

    return {
        "標題": title_property(title or "舞蹈分析"),
        "模式": select_property(str(summary.get("mode", "老師對比"))),
        "舞風": select_property(str(summary.get("dance_style", ""))),
        "平均分": {"number": float(summary.get("average_score", 0))},
        "弱點標籤": text_property(", ".join(str(tag) for tag in weakness_tags)),
        "一句話核心建議": text_property(str(summary.get("core_advice", ""))),
        "本週練習處方": text_property(format_practice_prescription(practice_prescription)),
        "下次檢查重點": text_property(", ".join(str(item) for item in next_check_focus)),
        "老師影片檔名": text_property(str(teacher_video.get("filename", ""))),
        "我的影片檔名": text_property(str(student_video.get("filename", ""))),
        "老師影片 Drive 連結": url_property(str(teacher_video.get("google_drive_url", ""))),
        "我的影片 Drive 連結": url_property(str(student_video.get("google_drive_url", ""))),
        "老師影片 Gemini File ID": text_property(str(teacher_video.get("gemini_file_id", ""))),
        "我的影片 Gemini File ID": text_property(str(student_video.get("gemini_file_id", ""))),
        "完整報告": text_property(report),
    }


def write_dance_report_to_notion(summary: dict[str, Any], report: str) -> dict[str, Any]:
    load_dotenv()
    token = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_DANCE_DATABASE_ID")
    if not token:
        raise NotionConfigError("找不到 NOTION_API_KEY。請確認 .env 已設定。")
    if not database_id:
        raise NotionConfigError("找不到 NOTION_DANCE_DATABASE_ID。請確認 .env 已設定。")

    payload = {
        "parent": {"database_id": database_id},
        "properties": build_notion_properties(summary, report),
    }
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=notion_headers(token),
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Notion 寫入失敗：HTTP {response.status_code} {response.text}")
    return response.json()
