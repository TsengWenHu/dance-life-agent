from __future__ import annotations

import argparse
import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/drive.file"]
DEFAULT_HERMES_AGENT_HOME = Path(os.getenv("HERMES_AGENT_HOME", "/root/hermes-agent"))
DEFAULT_CREDENTIALS_PATH = DEFAULT_HERMES_AGENT_HOME / "credentials.json"
DEFAULT_TOKEN_PATH = DEFAULT_HERMES_AGENT_HOME / "token.json"
DEFAULT_MODE = "老師對比"


@dataclass(frozen=True)
class DriveUploadResult:
    file_id: str
    name: str
    web_view_link: str


class DriveConfigError(RuntimeError):
    pass


def get_env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    return Path(value).expanduser() if value else default


def load_drive_credentials(credentials_path: Path, token_path: Path) -> Credentials:
    if not credentials_path.exists():
        raise DriveConfigError(f"找不到 Google Drive credentials：{credentials_path}")

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def build_drive_service(credentials_path: Path, token_path: Path):
    creds = load_drive_credentials(credentials_path, token_path)
    return build("drive", "v3", credentials=creds)


def today_taipei_compact() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y%m%d")


def clean_filename_part(value: str) -> str:
    return (
        value.strip()
        .replace("/", "-")
        .replace("\\", "-")
        .replace(":", "-")
        .replace(" ", "-")
    )


def build_dance_drive_name(file_path: Path, report_date: str, dance_style: str, mode: str, role: str = "") -> str:
    parts = [
        clean_filename_part(report_date),
        clean_filename_part(dance_style),
        clean_filename_part(mode),
    ]
    if role:
        parts.append(clean_filename_part(role))
    return "_".join(parts) + file_path.suffix


def upload_file_to_drive(
    file_path: Path,
    folder_id: str,
    credentials_path: Path,
    token_path: Path,
    drive_filename: str | None = None,
) -> DriveUploadResult:
    if not folder_id:
        raise DriveConfigError("缺少 GOOGLE_DRIVE_FOLDER_ID 或 --folder-id")
    if not file_path.exists():
        raise FileNotFoundError(f"找不到要上傳的檔案：{file_path}")
    if not file_path.is_file():
        raise ValueError(f"不是檔案：{file_path}")

    service = build_drive_service(credentials_path, token_path)
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
    metadata = {"name": drive_filename or file_path.name, "parents": [folder_id]}

    created = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        )
        .execute()
    )
    return DriveUploadResult(
        file_id=created["id"],
        name=created["name"],
        web_view_link=created["webViewLink"],
    )


def parse_args() -> argparse.Namespace:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Upload a local file to Google Drive.")
    parser.add_argument("file", type=Path, help="要上傳的檔案路徑")
    parser.add_argument("--folder-id", default=os.getenv("GOOGLE_DRIVE_FOLDER_ID"), help="Google Drive folder ID")
    parser.add_argument(
        "--credentials",
        type=Path,
        default=get_env_path("GOOGLE_DRIVE_CREDENTIALS_PATH", DEFAULT_CREDENTIALS_PATH),
        help="OAuth credentials.json 路徑",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=get_env_path("GOOGLE_DRIVE_TOKEN_PATH", DEFAULT_TOKEN_PATH),
        help="授權 token.json 路徑",
    )
    parser.add_argument("--drive-filename", default=None, help="上傳到 Google Drive 時使用的檔名")
    parser.add_argument("--dance-style", choices=["hiphop", "street jazz"], default=None, help="用舞蹈命名格式時的舞風")
    parser.add_argument("--mode", default=DEFAULT_MODE, help=f"用舞蹈命名格式時的模式，預設 {DEFAULT_MODE}")
    parser.add_argument("--date", default=today_taipei_compact(), help="用舞蹈命名格式時的日期，格式 yyyymmdd")
    parser.add_argument("--role", default="", help="可選，用來避免老師/我的影片同名，例如 teacher 或 student")
    parser.add_argument(
        "--dance-filename",
        action="store_true",
        help="把 Drive 檔名改成 {日期}_{舞風}_{模式}{_role}.副檔名",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    drive_filename = args.drive_filename
    if args.dance_filename:
        if not args.dance_style:
            raise SystemExit("使用 --dance-filename 時必須提供 --dance-style")
        drive_filename = build_dance_drive_name(
            file_path=args.file,
            report_date=args.date,
            dance_style=args.dance_style,
            mode=args.mode,
            role=args.role,
        )

    try:
        result = upload_file_to_drive(
            file_path=args.file,
            folder_id=args.folder_id,
            credentials_path=args.credentials,
            token_path=args.token,
            drive_filename=drive_filename,
        )
    except DriveConfigError as exc:
        raise SystemExit(str(exc)) from exc

    print("Google Drive 上傳完成")
    print(f"file_id: {result.file_id}")
    print(f"name: {result.name}")
    print(f"url: {result.web_view_link}")


if __name__ == "__main__":
    main()
