import requests

MERCHANT_ID      = "YOUR-MERCHANT-ID-HERE"   # ← کد مرچنت خود را اینجا بگذارید
AMOUNT           = 9400000                    # ریال (۹۴۰٬۰۰۰ تومان)
CALLBACK_URL     = "https://masircenter.com/api/payment/callback"
ZARINPAL_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZARINPAL_VERIFY  = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZARINPAL_START   = "https://www.zarinpal.com/pg/StartPay/"


def request_payment(description):
    """
    درخواست پرداخت به زرین‌پال.
    در صورت موفقیت: {"ok": True, "authority": "...", "url": "..."}
    در صورت خطا:    {"ok": False, "error": "..."}
    """
    try:
        resp = requests.post(ZARINPAL_REQUEST, json={
            "merchant_id":  MERCHANT_ID,
            "amount":       AMOUNT,
            "callback_url": CALLBACK_URL,
            "description":  description,
        }, timeout=10)

        data = resp.json().get("data", {})
        code = data.get("code")

        if code == 100:
            authority = data["authority"]
            return {
                "ok":        True,
                "authority": authority,
                "url":       ZARINPAL_START + authority,
            }

        return {
            "ok":    False,
            "error": f"کد خطای زرین‌پال: {code}",
        }

    except requests.exceptions.Timeout:
        return {"ok": False, "error": "اتصال به زرین‌پال قطع شد"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def verify_payment(authority, status):
    """
    تأیید پرداخت بعد از بازگشت از درگاه.
    در صورت موفقیت: {"ok": True, "ref_id": "..."}
    در صورت خطا:    {"ok": False, "error": "..."}
    """
    if status != "OK":
        return {"ok": False, "error": "پرداخت توسط کاربر لغو شد"}

    try:
        resp = requests.post(ZARINPAL_VERIFY, json={
            "merchant_id": MERCHANT_ID,
            "amount":      AMOUNT,
            "authority":   authority,
        }, timeout=10)

        data = resp.json().get("data", {})
        code = data.get("code")

        # code 100 = موفق، code 101 = قبلاً تأیید شده (پرداخت تکراری)
        if code in (100, 101):
            return {
                "ok":     True,
                "ref_id": str(data.get("ref_id", "")),
            }

        return {
            "ok":    False,
            "error": f"تأیید پرداخت ناموفق — کد: {code}",
        }

    except requests.exceptions.Timeout:
        return {"ok": False, "error": "اتصال به زرین‌پال قطع شد"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
