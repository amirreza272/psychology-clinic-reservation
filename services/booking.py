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

# تعطیلات رسمی ایران — فرمت میلادی YYYY-MM-DD
HOLIDAYS = [
    # ─── ۱۴۰۴ ───
    "2025-03-20",  # ۲۹ اسفند — آخرین روز سال
    "2025-03-21",  # نوروز — ۱ فروردین
    "2025-03-22",  # نوروز — ۲ فروردین
    "2025-03-23",  # نوروز — ۳ فروردین
    "2025-03-24",  # نوروز — ۴ فروردین
    "2025-04-01",  # ۱۳ فروردین
    "2025-04-20",  # رحلت امام خمینی (۳۱ خرداد)  ← تاریخ دقیق هر سال متفاوت است
    "2025-06-21",  # قیام ۱۵ خرداد
    "2025-07-07",  # شهادت امام صادق (تقریبی)
    "2025-07-17",  # عید فطر (تقریبی)
    "2025-07-18",  # عید فطر — روز دوم
    "2025-09-23",  # عید قربان (تقریبی)
    "2025-10-01",  # عید غدیر (تقریبی)
    "2025-10-25",  # تاسوعا (تقریبی)
    "2025-10-26",  # عاشورا (تقریبی)
    "2025-11-03",  # اربعین (تقریبی)
    "2025-11-12",  # رحلت پیامبر (تقریبی)
    "2025-11-14",  # شهادت امام حسن (تقریبی)
    "2025-12-12",  # شهادت امام رضا (تقریبی)
    "2025-12-22",  # شهادت امام حسن عسکری (تقریبی)
    "2026-01-10",  # ولادت پیامبر (تقریبی)
    # ─── ۱۴۰۵ ───
    "2026-03-21",  # نوروز — ۱ فروردین
    "2026-03-22",  # نوروز — ۲ فروردین
    "2026-03-23",  # نوروز — ۳ فروردین
    "2026-03-24",  # نوروز — ۴ فروردین
    "2026-04-01",  # ۱۳ فروردین
    "2026-06-10",  # رحلت امام خمینی (تقریبی)
    "2026-06-11",  # قیام ۱۵ خرداد (تقریبی)
]


def is_friday(date_obj):
    return date_obj.weekday() == 4


def is_holiday(date_obj):
    return date_obj.strftime("%Y-%m-%d") in HOLIDAYS


def can_book_tomorrow():
    """اگر الان قبل از ساعت ۲۰ باشد، فردا قابل رزرو است."""
    return datetime.now().hour < 20


def get_available_days(days_ahead=60):
    """لیست روزهای آزاد ۶۰ روز آینده را برمی‌گرداند."""
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
    """ساعت‌های خالی یک روز را برمی‌گرداند."""
    slots = AVAILABLE_TIMES.copy()

    # ساعت ۲۱ فقط آنلاین
    if session_type == "inperson":
        slots = [t for t in slots if t != "21:00"]

    # ساعت‌های رزرو شده (فقط پرداخت‌های موفق)
    booked = Appointment.query.filter_by(
        date=date_str,
        payment_status="paid"
    ).all()

    booked_times = {a.time for a in booked}

    return [t for t in slots if t not in booked_times]


def validate_booking(date_str, time_str, session_type):
    """
    اعتبارسنجی کامل درخواست رزرو.
    در صورت خطا یک رشته پیام برمی‌گرداند.
    در صورت موفقیت None برمی‌گرداند.
    """
    # فرمت تاریخ
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "فرمت تاریخ نامعتبر است"

    today = datetime.now().date()

    # گذشته یا امروز
    if booking_date <= today:
        return "رزرو برای امروز یا گذشته مجاز نیست"

    # فردا بعد از ساعت ۲۰
    if booking_date == today + timedelta(days=1) and not can_book_tomorrow():
        return "رزرو فردا بعد از ساعت ۲۰ امکان‌پذیر نیست"

    # جمعه
    if is_friday(booking_date):
        return "رزرو در روز جمعه امکان‌پذیر نیست"

    # تعطیل رسمی
    if is_holiday(booking_date):
        return "این روز تعطیل رسمی است"

    # ساعت معتبر
    if time_str not in AVAILABLE_TIMES:
        return "ساعت انتخابی معتبر نیست"

    # ساعت ۲۱ فقط آنلاین
    if time_str == "21:00" and session_type == "inperson":
        return "ساعت ۲۱ فقط برای جلسات آنلاین قابل رزرو است"

    # تداخل رزرو
    conflict = Appointment.query.filter_by(
        date=date_str,
        time=time_str,
        payment_status="paid"
    ).first()

    if conflict:
        return "این ساعت قبلاً رزرو شده است"

    return None
