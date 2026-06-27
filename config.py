import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "change-this-to-a-random-secret"   # ← حتماً عوض کنید

    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(BASE_DIR, "database.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # مدت اعتبار session
    PERMANENT_SESSION_LIFETIME = 3600   # یک ساعت
