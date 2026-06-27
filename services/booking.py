from datetime import datetime, timedelta
from models import Appointment


AVAILABLE_TIMES = [
    "11:15",
    "16:00",
    "17:00",
    "18:30",
    "19:30",
    "21:00",
]

# ─── تعطیلات رسمی ────────────────────────────────────────────
# فرمت: YYYY-MM-DD میلادی
# برای اضافه کردن تعطیل جدید، فقط یک خط به این لیست اضافه کنید.
# تعطیلات مذهبی (عاشورا، عید فطر و ...) هر سال تغییر می‌کنند —
# تاریخ دقیق را از تقویم رسمی ایران بگیرید.

HOLIDAYS = [
    # ─── ثابت هر سال (شمسی → میلادی ۱۴۰۴/۱۴۰۵) ───
    "2025-03-20",  # ۲۹ اسفند ۱۴۰۳
    "2025-03-21",  # ۱ فروردین — نوروز
    "2025-03-22",  # ۲ فروردین
    "2025-03-23",  # ۳ فروردین
    "2025-03-24",  # ۴ فروردین
    "2025-04-01",  # ۱۳ فروردین
    "2025-05-07",  # ۱۷ اردیبهشت — رحلت امام خمینی
    "2025-05-08",  # ۱۸ اردیبهشت — قیام ۱۵ خرداد
    "2025-08-21",  # ۳۰ مرداد — شهادت رجایی و باهنر
    "2026-02-11",  # ۲۲ بهمن — پیروزی انقلاب
    "2026-03-16",  # ۲۵ اسفند — ملی شدن نفت

    # ─── مذهبی ۱۴۰۴ (تاریخ دقیق بر اساس اعلام رسمی) ───
    "2025-07-17",  # عید فطر
    "2025-07-18",  # عید فطر — روز دوم
    "2025-09-24",  # عید قربان
    "2025-10-01",  # عید غدیر
    "2025-10-25",  # تاسوعا
    "2025-10-26",  # عاشورا
    "2025-11-04",  # اربعین
    "2025-11-13",  # رحلت پیامبر و شهادت امام حسن
    "2025-11-15",  # شهادت امام رضا
    "2025-12-13",  # شهادت امام حسن عسکری
    "2026-01-11",  # ولادت پیامبر و امام صادق

    # ─── نوروز ۱۴۰۵ ───
    "2026-03-21",  # ۱ فروردین
    "2026-03-22",  # ۲ فروردین
    "2026-03-23",  # ۳ فروردین
    "2026-03-24",  # ۴ فروردین
    "2026-04-02",  # ۱۳ فروردین
    "2026-05-27",  # رحلت امام خمینی (تقریبی ۱۴۰۵)
    "2026-05-28",  # قیام ۱۵ خرداد (تقریبی ۱۴۰۵)
]


def is_friday(date_obj):
    return date_obj.weekday() == 4


def is_holiday(date_obj):
    return date_obj.strftime("%Y-%m-%d") in HOLIDAYS


def can_book_tomorrow():
    """اگر الان قبل از ساعت ۲۰ باشد، فردا قابل رزرو است."""
    return datetime.now().hour < 20


def get_available_days(days_ahead=60):
    today = datetime.now().date()
    result = []

    for i in range(1, days_ahead + 1):
        target = today + timedelta(days=i)

        if i == 1 and not can_book_tomorrow():
            continue

        if is_friday(target):
            continue

        if is_holiday(target):
            continue

        result.append(target.strftime("%Y-%m-%d"))

    return result


def get_free_slots(date_str, session_type):
    slots = AVAILABLE_TIMES.copy()

    if session_type == "inperson":
        slots = [t for t in slots if t != "21:00"]

    booked = Appointment.query.filter_by(
        date=date_str,
        payment_status="paid"
    ).all()

    booked_times = {a.time for a in booked}
    return [t for t in slots if t not in booked_times]


def validate_booking(date_str, time_str, session_type):
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "فرمت تاریخ نامعتبر است"

    today = datetime.now().date()

    if booking_date <= today:
        return "رزرو برای امروز یا گذشته مجاز نیست"

    if booking_date == today + timedelta(days=1) and not can_book_tomorrow():
        return "رزرو فردا بعد از ساعت ۲۰ امکان‌پذیر نیست"

    if is_friday(booking_date):
        return "رزرو در روز جمعه امکان‌پذیر نیست"

    if is_holiday(booking_date):
        return "این روز تعطیل رسمی است"

    if time_str not in AVAILABLE_TIMES:
        return "ساعت انتخابی معتبر نیست"

    if time_str == "21:00" and session_type == "inperson":
        return "ساعت ۲۱ فقط برای جلسات آنلاین قابل رزرو است"

    conflict = Appointment.query.filter_by(
        date=date_str,
        time=time_str,
        payment_status="paid"
    ).first()

    if conflict:
        return "این ساعت قبلاً رزرو شده است"

    return None
