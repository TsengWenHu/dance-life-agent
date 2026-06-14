from __future__ import annotations

import argparse
import os
import random
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors

from .prompt import TeacherCompareRequest, build_teacher_compare_prompt
from .google_drive import (
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_MODE,
    DEFAULT_TOKEN_PATH,
    DriveConfigError,
    DriveUploadResult,
    build_dance_drive_name,
    get_env_path,
    today_taipei_compact,
    upload_file_to_drive,
)
from .notion_writer import (
    NotionConfigError,
    ReportJsonError,
    extract_report_json,
    write_dance_report_to_notion,
)


DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_RETRIES = 4
DEFAULT_HERMES_AGENT_HOME = Path(os.getenv("HERMES_AGENT_HOME", "/root/hermes-agent"))
DEFAULT_ENV_PATH = DEFAULT_HERMES_AGENT_HOME / ".env"


class GeminiConfigError(RuntimeError):
    pass


def build_client() -> genai.Client:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiConfigError(
            f"找不到 GEMINI_API_KEY。請在 {DEFAULT_ENV_PATH} 加上：\n"
            "GEMINI_API_KEY=你的_api_key"
        )
    return genai.Client(api_key=api_key)


def upload_and_wait(client: genai.Client, video_path: Path, label: str, poll_seconds: int = 5):
    if not video_path.exists():
        raise FileNotFoundError(f"{label} 不存在：{video_path}")
    if not video_path.is_file():
        raise ValueError(f"{label} 不是檔案：{video_path}")

    print(f"上傳{label}：{video_path}")
    uploaded = client.files.upload(file=video_path)

    while not uploaded.state or uploaded.state.name != "ACTIVE":
        if uploaded.state and uploaded.state.name == "FAILED":
            raise RuntimeError(f"{label} 處理失敗：{uploaded.name}")
        print(f"{label}處理中，目前狀態：{uploaded.state.name if uploaded.state else 'UNKNOWN'}")
        time.sleep(poll_seconds)
        uploaded = client.files.get(name=uploaded.name)

    print(f"{label}已就緒：{uploaded.name}")
    return uploaded


def is_non_retryable_quota_error(exc: errors.APIError) -> bool:
    message = str(exc)
    return "limit: 0" in message or "GenerateRequestsPerDayPerProjectPerModel-FreeTier" in message


def retry_delay_seconds(exc: errors.APIError, attempt: int) -> float:
    match = re.search(r"retryDelay': '(\d+)s'", str(exc))
    if match:
        return float(match.group(1))

    base_delay = min(60, 2**attempt)
    return base_delay + random.uniform(0, 1.5)


def generate_content_with_retry(client: genai.Client, model: str, contents: list, max_retries: int) -> str:
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(model=model, contents=contents)
            return response.text or ""
        except errors.APIError as exc:
            status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            retryable = status_code in {429, 500, 502, 503, 504}

            if status_code == 429 and is_non_retryable_quota_error(exc):
                raise RuntimeError(
                    f"Gemini model {model} 目前沒有可用免費額度，請改用其他模型或升級/調整 billing。"
                ) from exc

            if not retryable or attempt >= max_retries:
                raise

            delay = retry_delay_seconds(exc, attempt)
            print(f"Gemini 暫時無法回應（HTTP {status_code}），{delay:.1f} 秒後重試 {attempt + 1}/{max_retries}...")
            time.sleep(delay)

    raise RuntimeError("Gemini retry loop ended unexpectedly.")


def analyze_dance(
    teacher_video_path: Path,
    student_video_path: Path,
    dance_style: str,
    level: str = "請 AI 從影片判斷",
    focus: str = "想要跳好看，請 AI 自行診斷本週最值得改善的具體目標",
    model: str = DEFAULT_MODEL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    upload_drive: bool = False,
    drive_folder_id: str | None = None,
    drive_credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    drive_token_path: Path = DEFAULT_TOKEN_PATH,
    drive_date: str | None = None,
) -> str:
    teacher_drive: DriveUploadResult | None = None
    student_drive: DriveUploadResult | None = None
    if upload_drive:
        drive_date = drive_date or today_taipei_compact()
        print("上傳老師影片到 Google Drive...")
        teacher_drive = upload_file_to_drive(
            file_path=teacher_video_path,
            folder_id=drive_folder_id or "",
            credentials_path=drive_credentials_path,
            token_path=drive_token_path,
            drive_filename=build_dance_drive_name(
                file_path=teacher_video_path,
                report_date=drive_date,
                dance_style=dance_style,
                mode=DEFAULT_MODE,
                role="teacher",
            ),
        )
        print(f"老師影片 Drive URL：{teacher_drive.web_view_link}")

        print("上傳我的影片到 Google Drive...")
        student_drive = upload_file_to_drive(
            file_path=student_video_path,
            folder_id=drive_folder_id or "",
            credentials_path=drive_credentials_path,
            token_path=drive_token_path,
            drive_filename=build_dance_drive_name(
                file_path=student_video_path,
                report_date=drive_date,
                dance_style=dance_style,
                mode=DEFAULT_MODE,
                role="student",
            ),
        )
        print(f"我的影片 Drive URL：{student_drive.web_view_link}")

    client = build_client()

    teacher_file = upload_and_wait(client, teacher_video_path, "老師影片")
    student_file = upload_and_wait(client, student_video_path, "我的影片")

    prompt = build_teacher_compare_prompt(
        TeacherCompareRequest(
            teacher_video=teacher_video_path.name,
            student_video=student_video_path.name,
            dance_style=dance_style,  # argparse limits accepted values.
            level=level,
            focus=focus,
            teacher_video_path=str(teacher_video_path.resolve()),
            student_video_path=str(student_video_path.resolve()),
            teacher_google_drive_file_id=teacher_drive.file_id if teacher_drive else "",
            student_google_drive_file_id=student_drive.file_id if student_drive else "",
            teacher_google_drive_url=teacher_drive.web_view_link if teacher_drive else "",
            student_google_drive_url=student_drive.web_view_link if student_drive else "",
            teacher_gemini_file_id=teacher_file.name or "",
            student_gemini_file_id=student_file.name or "",
        )
    )

    print(f"呼叫 Gemini model：{model}")
    return generate_content_with_retry(
        client=client,
        model=model,
        contents=[
            "老師示範影片：",
            teacher_file,
            "我的練習影片：",
            student_file,
            prompt,
        ],
        max_retries=max_retries,
    )


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Analyze two dance videos with Gemini teacher comparison mode.")
    parser.add_argument("--teacher-video", required=True, type=Path, help="老師示範影片路徑")
    parser.add_argument("--student-video", required=True, type=Path, help="我的練習影片路徑")
    parser.add_argument("--dance-style", required=True, choices=["hiphop", "street jazz"], help="舞風")
    parser.add_argument("--level", default="請 AI 從影片判斷", help="可選；預設請 AI 從影片判斷")
    parser.add_argument(
        "--focus",
        default="想要跳好看，請 AI 自行診斷本週最值得改善的具體目標",
        help="可選；預設讓 AI 自行診斷改善目標",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model，預設 {DEFAULT_MODEL}")
    parser.add_argument("--max-retries", default=DEFAULT_MAX_RETRIES, type=int, help="Gemini 暫時性錯誤的最大重試次數")
    parser.add_argument("--upload-drive", action="store_true", help="分析前先把兩支影片上傳到 Google Drive")
    parser.add_argument("--drive-folder-id", default=os.getenv("GOOGLE_DRIVE_FOLDER_ID"), help="Google Drive folder ID")
    parser.add_argument(
        "--drive-credentials",
        type=Path,
        default=get_env_path("GOOGLE_DRIVE_CREDENTIALS_PATH", DEFAULT_CREDENTIALS_PATH),
        help="Google Drive OAuth credentials.json 路徑",
    )
    parser.add_argument(
        "--drive-token",
        type=Path,
        default=get_env_path("GOOGLE_DRIVE_TOKEN_PATH", DEFAULT_TOKEN_PATH),
        help="Google Drive token.json 路徑",
    )
    parser.add_argument("--drive-date", default=today_taipei_compact(), help="Drive 檔名日期，格式 yyyymmdd")
    parser.add_argument("--write-notion", action="store_true", help="將 Gemini 報告與 JSON 摘要寫入 Notion")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        report = analyze_dance(
            teacher_video_path=args.teacher_video,
            student_video_path=args.student_video,
            dance_style=args.dance_style,
            level=args.level,
            focus=args.focus,
            model=args.model,
            max_retries=args.max_retries,
            upload_drive=args.upload_drive,
            drive_folder_id=args.drive_folder_id,
            drive_credentials_path=args.drive_credentials,
            drive_token_path=args.drive_token,
            drive_date=args.drive_date,
        )
    except (GeminiConfigError, DriveConfigError) as exc:
        raise SystemExit(str(exc)) from exc
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    print("\n=== Gemini 舞蹈分析報告 ===\n")
    print(report)

    if args.write_notion:
        try:
            summary = extract_report_json(report)
            page = write_dance_report_to_notion(summary, report)
        except (NotionConfigError, ReportJsonError, RuntimeError) as exc:
            raise SystemExit(str(exc)) from exc
        print("\n=== Notion 寫入完成 ===\n")
        print(f"page_id: {page.get('id')}")
        print(f"url: {page.get('url')}")


if __name__ == "__main__":
    main()
