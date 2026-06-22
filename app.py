from flask import Flask, jsonify, request
from datetime import datetime, timedelta

from config import Config
from models import db, Appointment

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()


AVAILABLE_TIMES = [
    "17:00",
    "18:00",
    "19:00",
    "20:00",
    "21:00"
]


@app.route("/")
def home():
    return "Clinic Booking System Running 😎"

@app.route("/api/test-book")
def test_book():

    appointment = Appointment(
        name="Test User",
        phone="09120000000",
        date="2026-06-20",
        time="17:00",
        session_type="offline"
    )

    db.session.add(appointment)
    db.session.commit()

    return "Booked"

@app.route("/api/appointments")
def appointments():

    items = Appointment.query.order_by(
        Appointment.created_at.desc()
    ).all()

    return jsonify([
        item.to_dict()
        for item in items
    ])


@app.route("/api/book", methods=["POST"])
def book():

    data = request.get_json()

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    date = data.get("date", "").strip()
    time = data.get("time", "").strip()
    session_type = data.get("session_type", "").strip()

    if not all([name, phone, date, time, session_type]):
        return jsonify({
            "success": False,
            "message": "تمام فیلدها الزامی هستند"
        }), 400

    if time not in AVAILABLE_TIMES:
        return jsonify({
            "success": False,
            "message": "ساعت انتخابی معتبر نیست"
        }), 400

    if time == "21:00" and session_type != "online":
        return jsonify({
            "success": False,
            "message": "ساعت 21 فقط آنلاین است"
        }), 400

    try:
        booking_date = datetime.strptime(
            date,
            "%Y-%m-%d"
        ).date()

    except Exception:
        return jsonify({
            "success": False,
            "message": "فرمت تاریخ نامعتبر است"
        }), 400

    tomorrow = datetime.now().date() + timedelta(days=1)

    if booking_date < tomorrow:
        return jsonify({
            "success": False,
            "message": "رزرو برای امروز مجاز نیست"
        }), 400

    existing = Appointment.query.filter_by(
        date=date,
        time=time
    ).first()

    if existing:
        return jsonify({
            "success": False,
            "message": "این ساعت قبلاً رزرو شده"
        }), 400

    appointment = Appointment(
        name=name,
        phone=phone,
        date=date,
        time=time,
        session_type=session_type
    )

    db.session.add(appointment)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "نوبت با موفقیت ثبت شد",
        "appointment_id": appointment.id
    })


application = app