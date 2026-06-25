from flask import Flask, jsonify, request, render_template
from datetime import datetime, timedelta

from config import Config
from models import db, Appointment

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    db.create_all()


# ─── تنظیمات ───────────────────────────────────────────
AVAILABLE_TIMES = [
    "11:15",
    "16:00",
    "17:00",
    "18:30",
    "19:30",
    "21:00",
]

# تعطیلات رسمی - بعداً کامل می‌کنیم
HOLIDAYS = [
    "2026-03-20",  # نوروز
    "2026-03-21",
    "2026-03-22",
    "2026-03-23",
    "2026-03-24",
    "2026-03-25",
    "2026-03-26",
    "2026-03-27",
    "2026-03-28",
    "2026-03-29",
]


# ─── توابع کمکی ────────────────────────────────────────
def is_friday(date_obj):
    # در پایتون weekday(): شنبه=5، جمعه=4
    return date_obj.weekday() == 4


def is_holiday(date_obj):
    return date_obj.strftime("%Y-%m-%d") in HOLIDAYS


def can_book_tomorrow():
    """اگر الان بعد از ساعت 20 باشه، فردا قفله"""
    return datetime.now().hour < 20


def get_booked_times(date_str):
    """ساعت‌هایی که برای این تاریخ پرداخت شده"""
    booked = Appointment.query.filter_by(
        date=date_str,
        payment_status="paid"
    ).all()
    return [a.time for a in booked]


# ─── صفحه اصلی ─────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


# ─── API: روزهای مجاز ──────────────────────────────────
@app.route("/api/available-days")
def available_days():
    """
    برمی‌گردونه: لیست تاریخ‌های میلادی که قابل رزروه
    مثال: ["2026-06-23", "2026-06-24", ...]
    """
    today = datetime.now().date()
    result = []

    for i in range(1, 60):  # 60 روز آینده
        target = today + timedelta(days=i)

        # فردا بعد از ساعت 20 قفله
        if i == 1 and not can_book_tomorrow():
            continue

        # جمعه ممنوع
        if is_friday(target):
            continue

        # تعطیلات رسمی ممنوع
        if is_holiday(target):
            continue

        result.append(target.strftime("%Y-%m-%d"))

    return jsonify({
        "success": True,
        "days": result
    })


# ─── API: ساعت‌های آزاد ────────────────────────────────
@app.route("/api/slots")
def slots():
    """
    پارامترها:
      date: تاریخ میلادی (2026-06-23)
      type: online | inperson

    برمی‌گردونه: لیست ساعت‌های آزاد
    """
    date_str = request.args.get("date", "").strip()
    session_type = request.args.get("type", "online").strip()

    if not date_str:
        return jsonify({
            "success": False,
            "message": "date الزامی است"
        }), 400

    # بررسی فرمت تاریخ
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({
            "success": False,
            "message": "فرمت تاریخ نامعتبر است"
        }), 400

    # بررسی اینکه تاریخ مجاز باشه
    today = datetime.now().date()

    if date_obj <= today:
        return jsonify({
            "success": False,
            "message": "رزرو برای امروز یا گذشته ممنوع است"
        }), 400

    if is_friday(date_obj):
        return jsonify({
            "success": False,
            "message": "جمعه‌ها تعطیل است"
        }), 400

    if is_holiday(date_obj):
        return jsonify({
            "success": False,
            "message": "این روز تعطیل رسمی است"
        }), 400

    # ساعت‌های مجاز بر اساس نوع جلسه
    times = AVAILABLE_TIMES.copy()

    if session_type == "inperson":
        # حضوری: ساعت 21 نداره
        times = [t for t in times if t != "21:00"]

    # حذف ساعت‌های رزرو شده
    booked = get_booked_times(date_str)
    free = [t for t in times if t not in booked]

    return jsonify({
        "success": True,
        "date": date_str,
        "session_type": session_type,
        "slots": free
    })


# ─── API: ثبت نوبت ─────────────────────────────────────
@app.route("/api/book", methods=["POST"])
def book():
    data = request.get_json()

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    date_str = data.get("date", "").strip()
    time = data.get("time", "").strip()
    session_type = data.get("session_type", "").strip()
    notes = data.get("notes", "").strip()

    # اعتبارسنجی فیلدهای اجباری
    if not all([name, phone, date_str, time, session_type]):
        return jsonify({
            "success": False,
            "message": "همه فیلدها الزامی هستند"
        }), 400

    if time not in AVAILABLE_TIMES:
        return jsonify({
            "success": False,
            "message": "ساعت انتخابی معتبر نیست"
        }), 400

    if time == "21:00" and session_type == "inperson":
        return jsonify({
            "success": False,
            "message": "ساعت ۲۱ فقط برای جلسات آنلاین است"
        }), 400

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({
            "success": False,
            "message": "فرمت تاریخ نامعتبر است"
        }), 400

    today = datetime.now().date()

    if date_obj <= today:
        return jsonify({
            "success": False,
            "message": "رزرو برای امروز یا گذشته ممنوع است"
        }), 400

    # بررسی تکراری بودن
    existing = Appointment.query.filter_by(
        date=date_str,
        time=time,
        payment_status="paid"
    ).first()

    if existing:
        return jsonify({
            "success": False,
            "message": "این ساعت قبلاً رزرو شده است"
        }), 400

    # ثبت نوبت (هنوز pending - تا پرداخت نشه confirmed نمیشه)
    appointment = Appointment(
        name=name,
        phone=phone,
        date=date_str,
        time=time,
        session_type=session_type,
        notes=notes,
        payment_status="pending"
    )

    db.session.add(appointment)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "نوبت ثبت شد - لطفاً پرداخت را انجام دهید",
        "appointment_id": appointment.id
    })


# ─── API: لیست نوبت‌ها (برای پنل مدیریت) ──────────────
@app.route("/api/appointments")
def appointments():
    items = Appointment.query.order_by(
        Appointment.created_at.desc()
    ).all()

    return jsonify([i.to_dict() for i in items])


# ─── API: سلامت سیستم ──────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "time": datetime.now().isoformat()
    })


application = app
