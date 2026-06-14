from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo


DanceStyle = Literal["hiphop", "street jazz"]


@dataclass(frozen=True)
class TeacherCompareRequest:
    teacher_video: str
    student_video: str
    dance_style: DanceStyle
    level: str = "請 AI 從影片判斷"
    focus: str = "想要跳好看，請 AI 自行診斷本週最值得改善的具體目標"
    report_date: str | None = None
    teacher_video_path: str = ""
    student_video_path: str = ""
    teacher_google_drive_file_id: str = ""
    student_google_drive_file_id: str = ""
    teacher_google_drive_url: str = ""
    student_google_drive_url: str = ""
    teacher_gemini_file_id: str = ""
    student_gemini_file_id: str = ""


def today_taipei() -> str:
    return datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d")


def build_teacher_compare_prompt(request: TeacherCompareRequest) -> str:
    report_date = request.report_date or today_taipei()

    return f"""# Role
你是一位專業的街舞教練，擅長觀察身體線條、律動層次、重心控制、節奏落點與音樂性。

# Context
請對比附件中的兩支影片：
- 老師示範影片：{request.teacher_video}
- 我的練習影片：{request.student_video}
- 舞風：{request.dance_style}
- 我的程度：{request.level}
- 我的主觀目標：{request.focus}
- 今日日期：{report_date}

請注意：使用者通常無法準確判斷自己的程度或具體弱點。若「我的程度」或「我的主觀目標」不具體，請你根據影片自行判斷目前程度、核心問題與本週最值得改善的具體目標。不要要求使用者先自我診斷。

# First Step: 影片可分析性檢查
在正式分析前，請先檢查：
1. 兩支影片是否都能看到全身。
2. 是否有鏡像或左右顛倒的可能。
3. 音樂是否清楚。
4. 兩支影片是否可能從不同拍點或不同段落開始。
5. 是否有遮擋、畫質、角度或幀率問題會影響判斷。

如果有上述問題，請先說明這會如何影響分析可信度，但仍盡量分析可判斷的部分。

# Task
請針對老師影片與我的影片進行具體、嚴格、可量化的對比分析。

每個關鍵差異都必須包含：
1. 時間點或時間區間。
2. 老師怎麼做。
3. 我怎麼做。
4. 差異造成的視覺效果。
5. 具體修正方法。
6. 時間可信度：高 / 中 / 低。

請最多挑出 3 個本週最值得優先修正的問題，不要列太多。

# 舞風判斷標準
如果舞風是 hiphop，請特別觀察：
- groove 是否穩定
- bounce / rock 是否持續
- 下盤是否有重量
- 重心轉移是否準確落拍
- 動作鬆緊與音樂層次
- 動作是否只有形狀，缺少身體內在律動

如果舞風是 street jazz，請特別觀察：
- 線條延伸是否完整
- 手臂路徑是否乾淨
- 角度是否明確
- 軀幹控制與背部張力
- 爆發與收束是否清楚
- 表演張力是否持續

# 評分規則
請以 1-10 分評分：
- 穩定度
- 張力
- 音樂性
- 重心控制
- 動作完成度
- Flow / 連接性

分數請嚴格但合理，並用一句話解釋扣分原因。分數的目的是追蹤進步，不是安慰。

# Output Format

### {report_date} 舞蹈分析報告

#### 影片可分析性檢查
- 全身入鏡：
- 鏡像 / 左右判斷：
- 音樂清晰度：
- 影片同步狀態：
- 分析可信度：

#### 量化評分
- 穩定度：__/10
- 張力：__/10
- 音樂性：__/10
- 重心控制：__/10
- 動作完成度：__/10
- Flow / 連接性：__/10
- 平均分：__/10

#### 本次總評
[一句話說明這次最核心的問題與進步方向]

#### 關鍵分析
1. 時間點 / 時間區間：
   - 老師怎麼做：
   - 我怎麼做：
   - 差異造成的視覺效果：
   - 教練判斷：
   - 改善方法：
   - 時間可信度：

2. 時間點 / 時間區間：
   - 老師怎麼做：
   - 我怎麼做：
   - 差異造成的視覺效果：
   - 教練判斷：
   - 改善方法：
   - 時間可信度：

3. 時間點 / 時間區間：
   - 老師怎麼做：
   - 我怎麼做：
   - 差異造成的視覺效果：
   - 教練判斷：
   - 改善方法：
   - 時間可信度：

#### 弱點標籤
[#tag, #tag, #tag]

#### 本週練習處方
1. [練習名稱]
   - 目的：
   - 做法：
   - 次數 / 時長：
   - 檢查標準：

2. [練習名稱]
   - 目的：
   - 做法：
   - 次數 / 時長：
   - 檢查標準：

#### 下次影片優先檢查
- [重點 1]
- [重點 2]
- [重點 3]

#### Notion 欄位摘要
| 日期 | 模式 | 舞風 | 平均分 | 弱點標籤 | 一句話核心建議 | 本週練習處方 | 下次檢查重點 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| {report_date} | 老師對比 | {request.dance_style} | [平均分] | [標籤] | [建議] | [處方] | [檢查重點] |

#### JSON 摘要
請在報告最後額外輸出一段 fenced JSON，供程式寫入 Notion。JSON 必須可被標準 JSON parser 解析：

```json
{{
  "date": "{report_date}",
  "mode": "老師對比",
  "dance_style": "{request.dance_style}",
  "average_score": 0.0,
  "scores": {{
    "stability": 0,
    "tension": 0,
    "musicality": 0,
    "weight_control": 0,
    "completion": 0,
    "flow": 0
  }},
  "source_videos": {{
    "teacher_video": {{
      "filename": "{request.teacher_video}",
      "local_path": "{request.teacher_video_path}",
      "google_drive_file_id": "{request.teacher_google_drive_file_id}",
      "google_drive_url": "{request.teacher_google_drive_url}",
      "gemini_file_id": "{request.teacher_gemini_file_id}"
    }},
    "student_video": {{
      "filename": "{request.student_video}",
      "local_path": "{request.student_video_path}",
      "google_drive_file_id": "{request.student_google_drive_file_id}",
      "google_drive_url": "{request.student_google_drive_url}",
      "gemini_file_id": "{request.student_gemini_file_id}"
    }}
  }},
  "weakness_tags": ["tag1", "tag2", "tag3"],
  "core_advice": "一句話核心建議",
  "practice_prescription": [
    {{
      "name": "練習名稱",
      "purpose": "目的",
      "method": "做法",
      "duration": "次數 / 時長",
      "check_standard": "檢查標準"
    }}
  ],
  "next_check_focus": ["重點 1", "重點 2", "重點 3"]
}}
```

JSON 規則：
- 不要在 JSON 中加入 markdown。
- 不要在 JSON 中加入註解。
- `average_score` 必須是數字。
- `scores` 的六個分數必須是數字。
- `source_videos` 必須保留上述所有欄位，不要改欄位名稱。
- `weakness_tags` 不要包含 `#` 符號，只放純文字標籤。
- `practice_prescription` 最多 3 項。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Gemini prompt for dance teacher comparison mode.")
    parser.add_argument("--teacher-video", required=True, help="老師示範影片檔名或描述")
    parser.add_argument("--student-video", required=True, help="我的練習影片檔名或描述")
    parser.add_argument("--dance-style", required=True, choices=["hiphop", "street jazz"], help="舞風")
    parser.add_argument("--level", default="請 AI 從影片判斷", help="可選；預設請 AI 從影片判斷")
    parser.add_argument(
        "--focus",
        default="想要跳好看，請 AI 自行診斷本週最值得改善的具體目標",
        help="可選；預設讓 AI 自行診斷改善目標",
    )
    parser.add_argument("--report-date", default=None, help="報告日期，預設為台北今天 YYYY-MM-DD")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    request = TeacherCompareRequest(
        teacher_video=args.teacher_video,
        student_video=args.student_video,
        dance_style=args.dance_style,
        level=args.level,
        focus=args.focus,
        report_date=args.report_date,
    )
    print(build_teacher_compare_prompt(request))


if __name__ == "__main__":
    main()
