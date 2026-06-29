from flask import Blueprint, jsonify, request, redirect, session, url_for
from extensions import db
from models import Appointment
from services.booking import validate_booking
from services.zarinpal import request_payment, verify_payment, get_amount

payment_bp = Blueprint("payment", __name__, url_prefix="/api/payment")


def home_url(params=""):
    """آدرس صفحه اصلی را با پارامتر می‌سازد."""
    base = url_for("main.index", _external=False)
    return f"{base}?{params}" if params else base


@payment_bp.route("/start", methods=["POST"])
def start():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "داده‌ای ارسال نشده است"}), 400

    name         = data.get("name", "").strip()
    phone        = data.get("phone", "").strip()
    date         = data.get("date", "").strip()
    time         = data.get("time", "").strip()
    session_type = data.get("session_type", "").strip()
    notes        = data.get("notes", "").strip()

    if not all([name, phone, date, time, session_type]):
        return jsonify({"success": False, "message": "تمام فیلدهای اجباری را پر کنید"}), 400

    if not (phone.startswith("09") and len(phone) == 11 and phone.isdigit()):
        return jsonify({"success": False, "message": "شماره موبایل معتبر نیست"}), 400

    error = validate_booking(date, time, session_type)
    if error:
        return jsonify({"success": False, "message": error}), 400

    session["pending_booking"] = {
        "name":         name,
        "phone":        phone,
        "date":         date,
        "time":         time,
        "session_type": session_type,
        "notes":        notes,
        "amount":       get_amount(session_type),
    }

    desc = f"رزرو جلسه مشاوره — {name} — {date} ساعت {time}"
    result = request_payment(desc, session_type)

    if not result["ok"]:
        return jsonify({"success": False, "message": result["error"]}), 502

    session["pending_booking"]["authority"] = result["authority"]

    return jsonify({"success": True, "payment_url": result["url"]})


@payment_bp.route("/callback")
def callback():
    authority = request.args.get("Authority", "")
    status    = request.args.get("Status", "")

    pending = session.get("pending_booking")

    if not pending or pending.get("authority") != authority:
        return redirect(home_url("error=invalid_session"))

    amount = pending.get("amount", get_amount(pending.get("session_type", "online")))
    result = verify_payment(authority, status, amount)

    if not result["ok"]:
        session.pop("pending_booking", None)
        return redirect(home_url("error=payment_failed"))

    # بررسی تداخل
    conflict = Appointment.query.filter_by(
        date=pending["date"],
        time=pending["time"],
        payment_status="paid"
    ).first()

    if conflict:
        session.pop("pending_booking", None)
        return redirect(home_url("error=slot_taken"))

    # پرداخت موفق → ثبت در دیتابیس
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

    ref = result["ref_id"]
    return redirect(home_url(f"success=1&ref={ref}"))
