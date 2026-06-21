def build_router_prompt(user_input: str, language: str = "zh") -> str:
    if language == "en":
        return f"""
You are an intent classifier for a dance practice assistant.

User input:
{user_input}

Return exactly one label:
- dance_analysis
- room_booking

Rules:
- If the user asks about studio availability, room booking, reservation process, room schedule, or open slots, return room_booking.
- If the user asks about dance technique, move corrections, posture, choreography ideas, or practice methods, return dance_analysis.
- Keywords like "practice room", "studio", "booking", "reservation", "availability", "slot" should map to room_booking.
- Even if words like "dance" appear, if the context is room or booking related, return room_booking.
- Return label only, no explanation.
"""

    return f"""
你是一個舞蹈練習助理的意圖分類器。

使用者輸入：
{user_input}

請從以下標籤中精準回傳一個：
- dance_analysis
- room_booking

規則：
- 如果使用者在詢問場地、練舞室、可預約時間、場地預約、場地空位、預約流程，請回傳 room_booking。
- 如果使用者在詢問舞蹈技巧、動作建議、動作要領、身體姿勢、編舞方法、練習方式，請回傳 dance_analysis。
- 「練舞室」「練習室」「可預約」「預約」「場地」「空檔」等詞語，應該判定為 room_booking。
- 即使「練舞」這個詞出現，只要語境是在問場地、預約、可預約等，仍應回傳 room_booking。
- 只回傳標籤，不要多加其他說明文字。
"""
