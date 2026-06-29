import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "SECRET_KEY"

    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(BASE_DIR, "database.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERMANENT_SESSION_LIFETIME = 3600  # یک ساعت

    # مهم: session باید در کل زیرپوشه /booking در دسترس باشد
    # نه فقط در /booking/api/payment/callback
    SESSION_COOKIE_PATH = "/"
