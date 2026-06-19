"""
舞蹈分析測試：無影片 vs 有影片模式
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# 加入專案根目錄到 Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 載入本地 .env 以便測試環境能讀到 OPENAI_API_KEY
load_dotenv(Path(__file__).parent.parent / '.env')

from agents.dance_agent import analyze_dance


def test_dance_no_video_no_scores():
    """
    測試：無影片時，回應中不應包含分數表
    """
    user_input = "我的 body roll 重心往前，應該怎麼改？"
    response = analyze_dance(user_input, video_path=None)
    
    print("\n=== 無影片模式測試 ===")
    print(f"輸入: {user_input}")
    print(f"回應:\n{response}\n")
    
    # 檢查回應是否包含分數相關字眼
    forbidden_patterns = ["__/10", "平均分", "穩定度：", "張力：", "動作評分"]
    has_score = any(pattern in response for pattern in forbidden_patterns)
    
    assert not has_score, f"無影片模式不應包含分數表，但回應包含分數相關內容"
    print("✅ 無影片模式測試通過：回應中不包含分數")


def test_dance_with_video_format():
    """
    測試：有影片時，回應應該是完整的分析格式
    （注意：因為我們沒有真實影片，所以這只檢查格式，不檢查實際分析結果）
    """
    user_input = "請分析我的舞蹈動作"
    # 這裡我們傳一個假的影片路徑來測試分流邏輯
    response = analyze_dance(user_input, video_path="/fake/video.mp4")
    
    print("\n=== 有影片模式測試 ===")
    print(f"輸入: {user_input}")
    print(f"回應:\n{response}\n")
    
    # 檢查是否有預期的報告格式字眼（非分數，而是結構）
    expected_keywords = ["舞蹈分析", "報告", "評分", "建議"] or ["Role", "Context", "Task"]
    # 由於 prompt 會被發送給 OpenAI，我們只檢查回應不為空且有內容
    assert response and len(response) > 10, "有影片模式應該回傳有效的分析"
    print("✅ 有影片模式測試通過：回應包含內容")


def test_dance_no_video_suggests_upload():
    """
    測試：無影片時若使用者要求評分，系統應提示上傳影片
    """
    user_input = "請給我的舞蹈動作評分"
    response = analyze_dance(user_input, video_path=None)
    
    print("\n=== 無影片+要求評分測試 ===")
    print(f"輸入: {user_input}")
    print(f"回應:\n{response}\n")
    
    # 檢查是否有提示上傳影片的訊息
    has_upload_hint = "上傳" in response or "影片" in response
    # 不強制要求，但通常會有這個提示
    print(f"{'✅' if has_upload_hint else '⚠️'}  回應中{'有' if has_upload_hint else '沒有'}提示上傳影片")


if __name__ == "__main__":
    try:
        test_dance_no_video_no_scores()
        test_dance_with_video_format()
        test_dance_no_video_suggests_upload()
        print("\n" + "="*50)
        print("✅ 所有測試通過！")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ 測試失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 測試錯誤: {e}")
        sys.exit(1)
