from datetime import datetime
from app import db


class AlertConfig(db.Model):
    __tablename__ = "alert_configs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    level = db.Column(
        db.Enum("INFO", "WASPADA", "SIAGA", "EVAKUASI"), nullable=False
    )
    min_water_level_cm = db.Column(db.Float, nullable=False)
    min_flood_probability = db.Column(db.Float, nullable=False, default=0)
    min_rainfall_mm = db.Column(db.Float, nullable=False, default=0)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class NotificationConfig(db.Model):
    __tablename__ = "notification_configs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    cooldown_minutes = db.Column(db.Integer, nullable=False, default=60)
    min_trigger_level = db.Column(
        db.Enum("INFO", "WASPADA", "SIAGA", "EVAKUASI"),
        nullable=False,
        default="SIAGA",
    )
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)


class WaRecipient(db.Model):
    __tablename__ = "wa_recipients"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    added_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone_number": self.phone_number,
            "is_active": self.is_active,
            "added_by": self.added_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
