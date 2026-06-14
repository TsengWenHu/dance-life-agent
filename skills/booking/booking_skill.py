"""
Practice Everything 練習室自動預約腳本

使用方式：
  python -m skills.booking.booking_skill

或從其他程式呼叫：
  from skills.booking import login, check_availability, make_booking
"""

import os
import re
import json
import urllib.parse
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://www.practice-everything-dm.com"

# 所有房間的 product slug 與 WooCommerce product ID
ROOM_PRODUCTS = {
    "Z01": {"slug": "z01", "id": "169690"},
    "Z02": {"slug": "z02", "id": "169685"},
    "Z03": {"slug": "z03", "id": "169686"},
    "Z04": {"slug": "z04", "id": "169687"},
    "Z05": {"slug": "z05", "id": "169688"},
    "Z06": {"slug": "z06", "id": "169689"},
    "Z07": {"slug": "z07", "id": "81476529"},
    "Z08": {"slug": "z08", "id": "81479305"},
    "Z09": {"slug": "z09", "id": "81479306"},
    "Z10": {"slug": "z10", "id": "81479307"},
    "Z11": {"slug": "z11", "id": "81479308"},
    "Z12": {"slug": "z12", "id": "81479309"},
    "Z13": {"slug": "z13", "id": "81479310"},
    "Z14": {"slug": "z14", "id": "81479312"},
    "Z15": {"slug": "z15", "id": "81484864"},
    "Z16": {"slug": "z16", "id": "81484868"},
    "Z17": {"slug": "z17", "id": "94617813"},
}

# 全局 session，登入後複用
_session = requests.Session()
_session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
})


# ──────────────────────────────────────────
# 內部工具函式
# ──────────────────────────────────────────

def _extract_input(html: str, name: str) -> str | None:
    """從 HTML 中取出指定 name 的 input 欄位值。"""
    soup = BeautifulSoup(html, "html.parser")
    el = soup.find("input", {"name": name})
    return el["value"] if el and el.get("value") else None


def _extract_js_var(html: str, var_name: str) -> dict:
    """從 HTML 的 <script> 中解析 JS 物件變數（僅支援 JSON-compatible 值）。"""
    pattern = rf'var\s+{re.escape(var_name)}\s*=\s*(\{{.*?\}});'
    m = re.search(pattern, html, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return {}


def _get_addon_value(html: str, product_id: str, duration_hours: float) -> str:
    """
    從產品頁 HTML 解析「加時租借」select 的選項，回傳符合 duration_hours 的 option value。
    若找不到對應時數則拋出 ValueError。
    """
    addon_key = f"addon-{product_id}-%e5%8a%a0%e6%99%82%e7%a7%9f%e5%80%9f-0"
    soup = BeautifulSoup(html, "html.parser")
    sel = soup.find("select", {"name": addon_key})
    if not sel:
        raise ValueError(f"找不到「加時租借」選單（product_id={product_id}）。")

    # 把時數轉成搜尋關鍵字，例如 1 → "1 hr", 1.5 → "1.5 hr"
    if duration_hours == 1.0:
        keywords = ["1hr", "1 hr", "不延長"]
    else:
        hr_str = str(duration_hours).rstrip("0").rstrip(".")
        keywords = [f"{hr_str} hr", f"{hr_str}hr", f"總計 {hr_str}"]

    for opt in sel.find_all("option"):
        text = opt.get_text()
        val = opt.get("value", "")
        if val and any(kw in text for kw in keywords):
            return val

    valid = [f"{o.get_text(strip=True)}" for o in sel.find_all("option") if o.get("value")]
    raise ValueError(
        f"找不到 {duration_hours} 小時的選項。可用選項：{valid}"
    )


def _appointment_form_data(
    product_id: str, csrf: str, month: str, day: str, year: str,
    time: str = "", addon_value: str = ""
) -> dict:
    """組裝 WooCommerce Appointments 預約表單欄位。"""
    addon_key = f"addon-{product_id}-%e5%8a%a0%e6%99%82%e7%a7%9f%e5%80%9f-0"
    return {
        "_csrf_token": csrf,
        "wc_appointments_field_start_date_month": month,
        "wc_appointments_field_start_date_day": day,
        "wc_appointments_field_start_date_year": year,
        "wc_appointments_field_start_date_time": time,
        "wc_appointments_field_addons_duration": "0",
        "wc_appointments_field_addons_cost": "0",
        addon_key: addon_value,
        "add-to-cart": product_id,
    }


def _clear_cart() -> int:
    """
    清空購物車中所有商品，回傳移除的商品數量。
    WooCommerce 的移除連結格式：/cart/?remove_item=HASH&_wpnonce=NONCE
    """
    resp = _session.get(f"{BASE_URL}/cart/")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    remove_links = soup.find_all("a", class_="remove")

    if not remove_links:
        return 0

    removed = 0
    for link in remove_links:
        href = link.get("href", "")
        if "remove_item" in href:
            _session.get(href, allow_redirects=True)
            removed += 1

    if removed:
        print(f"  購物車已清空（移除 {removed} 件商品）")
    return removed


# ──────────────────────────────────────────
# 公開 API
# ──────────────────────────────────────────

def login(email: str = None, password: str = None) -> bool:
    """
    登入 Practice Everything 帳號並保存 session。

    Args:
        email:    帳號 email；未傳入時從環境變數 PE_EMAIL 讀取。
        password: 密碼；未傳入時從環境變數 PE_PASSWORD 讀取。

    Returns:
        True 代表登入成功。

    Raises:
        ValueError: 登入失敗時包含錯誤訊息。
    """
    email = email or os.environ.get("PE_EMAIL")
    password = password or os.environ.get("PE_PASSWORD")
    if not email or not password:
        raise ValueError("請設定 PE_EMAIL 與 PE_PASSWORD 環境變數，或直接傳入參數。")

    # GET 登入頁取得 nonce
    resp = _session.get(f"{BASE_URL}/my-account/")
    resp.raise_for_status()

    nonce = _extract_input(resp.text, "woocommerce-login-nonce")
    referer = _extract_input(resp.text, "_wp_http_referer") or "/my-account/"

    if not nonce:
        raise ValueError("無法從登入頁取得 nonce，頁面結構可能已更改。")

    # POST 登入
    resp = _session.post(
        f"{BASE_URL}/my-account/",
        data={
            "username": email,
            "password": password,
            "login": "Log in",
            "woocommerce-login-nonce": nonce,
            "_wp_http_referer": referer,
        },
        headers={"Referer": f"{BASE_URL}/my-account/"},
        allow_redirects=True,
    )
    resp.raise_for_status()

    # 若登入後仍在 /my-account/ 且含有登入表單，代表失敗
    soup = BeautifulSoup(resp.text, "html.parser")
    error_el = soup.find(class_="woocommerce-error")
    if error_el:
        raise ValueError(f"登入失敗：{error_el.get_text(strip=True)}")

    login_form = soup.find("form", class_="woocommerce-form-login")
    if login_form:
        raise ValueError("登入失敗：帳號或密碼錯誤。")

    print(f"✓ 已登入：{email}")
    return True


def check_availability(
    date: str,
    duration_hours: int = 1,
    location: str = None,
) -> dict[str, list[str]]:
    """
    查詢指定日期的可預約時段。

    Args:
        date:           日期字串，格式 YYYY-MM-DD。
        duration_hours: 使用時數（預設 1 小時）。
        location:       指定房間名稱（如 'Z01'）；不傳則查詢所有房間。

    Returns:
        dict，key 為房間名稱，value 為可用時間字串清單（如 ['07:00', '08:30']）。
        已被預訂（slot_empty）或不開放的時段不會出現在清單中。
    """
    dt = datetime.strptime(date, "%Y-%m-%d")
    month = f"{dt.month:02d}"
    day = f"{dt.day:02d}"
    year = str(dt.year)

    rooms = [location.upper()] if location else list(ROOM_PRODUCTS.keys())
    results: dict[str, list[str]] = {}

    for room in rooms:
        if room not in ROOM_PRODUCTS:
            print(f"⚠ 未知房間：{room}，跳過。")
            continue

        info = ROOM_PRODUCTS[room]
        product_url = f"{BASE_URL}/product/{info['slug']}/"

        # 取得產品頁 → 提取 CSRF token 與 nonce
        resp = _session.get(product_url)
        resp.raise_for_status()

        params = _extract_js_var(resp.text, "wc_appointment_form_params")
        nonce = params.get("nonce_find_day_slots")
        csrf = _extract_input(resp.text, "_csrf_token") or ""

        if not nonce:
            print(f"⚠ {room}：無法取得 nonce，跳過。")
            continue

        # 取得 addon value（查詢時段不需要選時數，傳空值即可）
        try:
            addon_value = _get_addon_value(resp.text, info["id"], duration_hours)
        except ValueError:
            addon_value = ""  # 查詢時段時 addon 不影響結果

        # 組裝表單資料並 URL-encode（模擬瀏覽器 serialize()）
        form_fields = _appointment_form_data(info["id"], csrf, month, day, year, addon_value=addon_value)
        form_serialized = urllib.parse.urlencode(form_fields)

        # 呼叫 wc_appointments_get_slots
        resp = _session.post(
            f"{BASE_URL}/wp-admin/admin-ajax.php",
            data={
                "action": "wc_appointments_get_slots",
                "form": form_serialized,
                "nonce": nonce,
            },
            headers={
                "Referer": product_url,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        resp.raise_for_status()

        # 解析回傳 HTML，過濾掉已滿（slot_empty）的時段
        soup = BeautifulSoup(resp.text, "html.parser")
        slots = []
        for li in soup.find_all("li", class_="slot"):
            if "slot_empty" not in li.get("class", []):
                a = li.find("a")
                if a:
                    slots.append(a.get_text(strip=True))

        results[room] = slots
        print(f"  {room}：找到 {len(slots)} 個可用時段")

    return results


def make_booking(
    date: str,
    start_time: str,
    duration_hours: int,
    room: str,
) -> dict:
    """
    預約練習室。

    Args:
        date:           日期字串，格式 YYYY-MM-DD。
        start_time:     開始時間字串，格式 HH:MM（如 '10:00'）。
        duration_hours: 使用時數。
        room:           房間名稱（如 'Z01'）。

    Returns:
        dict 包含 success, order_id, order_url。

    Raises:
        ValueError: 加入購物車或結帳失敗時包含錯誤訊息。
    """
    room = room.upper()
    if room not in ROOM_PRODUCTS:
        raise ValueError(f"未知房間：{room}。有效房間：{list(ROOM_PRODUCTS.keys())}")

    info = ROOM_PRODUCTS[room]
    dt = datetime.strptime(date, "%Y-%m-%d")
    month = f"{dt.month:02d}"
    day = f"{dt.day:02d}"
    year = str(dt.year)
    product_url = f"{BASE_URL}/product/{info['slug']}/"

    # ── Step 1：清空購物車（避免舊商品干擾結帳）─────────────────
    _clear_cart()

    # ── Step 2：取得產品頁（CSRF token + addon 選項）─────────────
    resp = _session.get(product_url)
    resp.raise_for_status()
    csrf = _extract_input(resp.text, "_csrf_token") or ""
    addon_value = _get_addon_value(resp.text, info["id"], duration_hours)

    # ── Step 3：加入購物車 ─────────────────────────────────────
    cart_data = _appointment_form_data(info["id"], csrf, month, day, year, start_time, addon_value)

    resp = _session.post(
        product_url,
        data=cart_data,
        headers={"Referer": product_url},
        allow_redirects=True,
    )
    resp.raise_for_status()

    # 偵測加入購物車是否成功
    soup = BeautifulSoup(resp.text, "html.parser")
    error_el = soup.find(class_="woocommerce-error")
    if error_el:
        raise ValueError(f"加入購物車失敗：{error_el.get_text(strip=True)}")

    # WooCommerce 成功加入後通常在頁面顯示 .woocommerce-message 或導向購物車
    print(f"✓ 已加入購物車：{room} {date} {start_time}（{duration_hours}hr）")

    # ── Step 4：取得結帳頁 nonce 與帳單資訊 ─────────────────────
    resp = _session.get(f"{BASE_URL}/checkout/")
    resp.raise_for_status()

    checkout_html = resp.text
    soup = BeautifulSoup(checkout_html, "html.parser")

    def _field(name: str) -> str:
        el = soup.find("input", {"name": name}) or soup.find("select", {"name": name})
        return el["value"] if el and el.get("value") else ""

    checkout_nonce = _field("woocommerce-process-checkout-nonce")
    checkout_csrf = _field("_csrf_token")

    if not checkout_nonce:
        raise ValueError("無法從結帳頁取得 nonce，可能尚未登入或購物車為空。")

    # 檢查是否有「使用點數」選項，若有則先套用
    points_btn = soup.find("input", {"name": "wc_points_rewards_apply_discount"})
    if points_btn:
        print("  ✓ 偵測到點數折扣，套用中...")
        points_resp = _session.post(
            f"{BASE_URL}/cart/",
            data={
                "wc_points_rewards_apply_discount": points_btn.get("value", ""),
                "wc_points_rewards_apply_discount_amount": _field("wc_points_rewards_apply_discount_amount"),
            },
            headers={"Referer": f"{BASE_URL}/checkout/"},
            allow_redirects=True,
        )
        # 重新取得結帳頁（點數已套用）
        resp = _session.get(f"{BASE_URL}/checkout/")
        resp.raise_for_status()
        checkout_html = resp.text
        soup = BeautifulSoup(checkout_html, "html.parser")

    # 確認帳號身份
    billing_email = _field("billing_email")
    billing_name = _field("billing_first_name")
    print(f"✓ 結帳帳號確認： ({billing_email})")

    # 偵測所有可用的支付方式
    payment_methods = {}
    for input_el in soup.find_all("input", {"name": "payment_method"}):
        method_id = input_el.get("value", "")
        if method_id:
            label_el = input_el.find_parent().find("label")
            label_text = label_el.get_text(strip=True) if label_el else method_id
            payment_methods[method_id] = label_text

    if not payment_methods:
        raise ValueError("找不到任何支付方式，頁面結構可能已更改。")

    # 優先選用「點數」相關方式，否則用第一個
    payment_method = None
    for method_id, label in payment_methods.items():
        if "點" in label or "credit" in label.lower() or "balance" in label.lower():
            payment_method = method_id
            print(f"  ✓ 偵測到點數支付：{label}")
            break

    if not payment_method:
        payment_method = list(payment_methods.keys())[0]
        print(f"  ⚠ 未找到點數支付，使用預設方式：{payment_methods[payment_method]}")

    # ── Step 5：送出結帳（WooCommerce 用 AJAX endpoint，回傳 JSON）──
    checkout_data = {
        "_csrf_token": checkout_csrf,
        "billing_first_name": billing_name,
        "billing_email": billing_email,
        "billing_phone": _field("billing_phone"),
        "billing_custom_last5": _field("billing_custom_last5"),
        "shipping_first_name": "",
        "shipping_address_1": "",
        "order_comments": "",
        "payment_method": payment_method,
        "woocommerce-process-checkout-nonce": checkout_nonce,
        "_wp_http_referer": "/?wc-ajax=update_order_review",
    }

    resp = _session.post(
        f"{BASE_URL}/?wc-ajax=checkout",
        data=checkout_data,
        headers={
            "Referer": f"{BASE_URL}/checkout/",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        },
        allow_redirects=False,
    )
    resp.raise_for_status()

    # WooCommerce AJAX checkout 回傳 JSON
    try:
        result = resp.json()
    except Exception:
        raise ValueError(f"結帳回應格式錯誤（非 JSON）：{resp.text[:300]}")

    if result.get("result") == "success":
        redirect_url = result.get("redirect", "")
        m = re.search(r"order-received/(\d+)", redirect_url)
        order_id = m.group(1) if m else None
        print(f"✓ 預約成功！訂單 #{order_id}")
        print(f"  確認頁：{redirect_url}")
        return {"success": True, "order_id": order_id, "order_url": redirect_url}

    # 結帳失敗，解析 WooCommerce 回傳的 HTML 錯誤訊息
    messages_html = result.get("messages", "")
    if messages_html:
        err_soup = BeautifulSoup(messages_html, "html.parser")
        msg = err_soup.get_text(separator=" ", strip=True)
    else:
        msg = str(result)
    raise ValueError(f"結帳失敗：{msg}")


# # ──────────────────────────────────────────
# # 快速測試入口
# # ──────────────────────────────────────────

# if __name__ == "__main__":
#     import sys
#     from pprint import pprint

#     print("=" * 50)
#     print("Practice Everything 預約腳本測試")
#     print("=" * 50)

#     # 1. 登入
#     print("\n[1] 登入測試...")
#     try:
#         login()
#     except ValueError as e:
#         print(f"✗ 登入失敗：{e}")
#         sys.exit(1)

#     # 2. 查詢可用時段（只查 Z01，減少請求數）
#     test_date = datetime.now().strftime("%Y-%m-%d")
#     # 改成明天
#     from datetime import timedelta
#     test_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

#     print(f"\n[2] 查詢可用時段（{test_date}，只查 Z01）...")
#     try:
#         slots = check_availability(test_date, location="Z01")
#         pprint(slots)
#     except Exception as e:
#         print(f"✗ 查詢失敗：{e}")
#         sys.exit(1)

#     # 3. 預約測試（預設不執行，避免誤操作）
#     print("\n[3] 預約功能已就緒（測試時不自動執行，請手動呼叫 make_booking()）")
#     make_booking('2026-07-20', '19:00', 1.5, 'Z01')
#     print("    範例：make_booking('2026-05-20', '19:00', 1, 'Z01')")

#     print("\n✓ 所有測試完成！")
