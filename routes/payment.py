from flask import Blueprint, jsonify, request, redirect, session
from extensions import db
from models import Appointment
from services.booking import validate_booking
from services.zarinpal import request_payment, verify_payment

payment_bp = Blueprint("payment", __name__, url_prefix="/api/payment")


@payment_bp.route("/start", methods=["POST"])
def start():
    """
    ۱. اطلاعات رزرو را اعتبارسنجی می‌کند.
    ۲. اطلاعات را در session ذخیره می‌کند (هنوز در دیتابیس ثبت نمی‌شود).
    ۳. لینک درگاه زرین‌پال را برمی‌گرداند.
    """
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "داده‌ای ارسال نشده است"}), 400

    name         = data.get("name", "").strip()
    phone        = data.get("phone", "").strip()
    date         = data.get("date", "").strip()
    time         = data.get("time", "").strip()
    session_type = data.get("session_type", "").strip()
    notes        = data.get("notes", "").strip()

    # ─── اعتبارسنجی فیلدهای اجباری ─────────────────────────
    if not all([name, phone, date, time, session_type]):
        return jsonify({
            "success": False,
            "message": "تمام فیلدهای اجباری را پر کنید"
        }), 400

    if not (phone.startswith("09") and len(phone) == 11 and phone.isdigit()):
        return jsonify({
            "success": False,
            "message": "شماره موبایل معتبر نیست"
        }), 400

    # ─── اعتبارسنجی قوانین رزرو ─────────────────────────────
    error = validate_booking(date, time, session_type)
    if error:
        return jsonify({"success": False, "message": error}), 400

    # ─── ذخیره موقت در session (نه دیتابیس) ─────────────────
    session["pending_booking"] = {
        "name":         name,
        "phone":        phone,
        "date":         date,
        "time":         time,
        "session_type": session_type,
        "notes":        notes,
    }

    # ─── درخواست به زرین‌پال ─────────────────────────────────
    desc = f"رزرو جلسه مشاوره — {name} — {date} ساعت {time}"
    result = request_payment(desc)

    if not result["ok"]:
        return jsonify({
            "success": False,
            "message": result["error"]
        }), 502

    # authority را هم در session نگه می‌داریم برای تأیید بعدی
    session["pending_booking"]["authority"] = result["authority"]

    return jsonify({
        "success":   True,
        "payment_url": result["url"],
    })


@payment_bp.route("/callback")
def callback():
    """
    زرین‌پال کاربر را اینجا برمی‌گرداند.
    اگر پرداخت موفق بود → نوبت در دیتابیس ثبت می‌شود → صفحه موفقیت.
    اگر ناموفق بود → صفحه خطا.
    """
    authority = request.args.get("Authority", "")
    status    = request.args.get("Status", "")

    # بازیابی اطلاعات موقت از session
    pending = session.get("pending_booking")

    if not pending or pending.get("authority") != authority:
        return redirect("/?error=invalid_session")

    # ─── تأیید پرداخت با زرین‌پال ───────────────────────────
    result = verify_payment(authority, status)

    if not result["ok"]:
        session.pop("pending_booking", None)
        return redirect(f"/?error=payment_failed")

    # ─── پرداخت موفق → ثبت نوبت در دیتابیس ─────────────────
    # یک بار دیگر بررسی تداخل (احتمال race condition)
    conflict = Appointment.query.filter_by(
        date=pending["date"],
        time=pending["time"],
        payment_status="paid"
    ).first()

    if conflict:
        # این ساعت در فاصله پرداخت توسط نفر دیگری گرفته شد
        session.pop("pending_booking", None)
        return redirect("/?error=slot_taken")

    appointment = Appointment(
        name=pending["name"],
        phone=pending["phone"],
        date=pending["date"],
        time=pending["time"],
        session_type=pending["session_type"],
        notes=pending.get("notes", ""),
        payment_status="paid",
        authority=authority,
        ref_id=result["ref_id"],
    )

    db.session.add(appointment)
    db.session.commit()

    session.pop("pending_booking", None)

    return redirect(f"/?success=1&ref={result['ref_id']}")
