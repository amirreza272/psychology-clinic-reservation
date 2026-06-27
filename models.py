from datetime import datetime
from extensions import db


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)

    # اطلاعات مراجع
    name  = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20),  nullable=False)

    # زمان نوبت — date به فرمت میلادی: 2026-06-25
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)

    # online / inperson
    session_type = db.Column(db.String(20), nullable=False)

    # paid / cancelled
    payment_status = db.Column(
        db.String(20),
        nullable=False,
        default="paid"   # هر رکوردی که ثبت می‌شود قطعاً پرداخت شده
    )

    # زرین‌پال
    authority = db.Column(db.String(120))
    ref_id    = db.Column(db.String(120))

    # توضیحات مراجع
    notes = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    def to_dict(self):
        return {
            "id":             self.id,
            "name":           self.name,
            "phone":          self.phone,
            "date":           self.date,
            "time":           self.time,
            "session_type":   self.session_type,
            "payment_status": self.payment_status,
            "authority":      self.authority,
            "ref_id":         self.ref_id,
            "notes":          self.notes,
            "created_at":     self.created_at.isoformat(),
        }
