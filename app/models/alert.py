from app import db
from datetime import datetime
from app.models.config import WaRecipient, NotificationConfig

class AlertLevel(db.Model):
    __tablename__ = "alert_levels"

    id = db.Column(db.Integer, primary_key=True)
    sensor_reading_id = db.Column(db.Integer, db.ForeignKey("sensor_readings.id", ondelete="CASCADE"), nullable=False)
    ml_prediction_id = db.Column(db.Integer, db.ForeignKey("ml_predictions.id", ondelete="SET NULL"), nullable=True)
    level = db.Column(db.Enum("INFO", "WASPADA", "SIAGA", "EVAKUASI"), nullable=False)
    water_level_cm = db.Column(db.Float, nullable=False)
    flood_probability_24h = db.Column(db.Float, nullable=True)
    rainfall_mm = db.Column(db.Float, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    notifications = db.relationship("WaNotification", backref="alert_level", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "sensor_reading_id": self.sensor_reading_id,
            "ml_prediction_id": self.ml_prediction_id,
            "level": self.level,
            "water_level_cm": self.water_level_cm,
            "flood_probability_24h": self.flood_probability_24h,
            "rainfall_mm": self.rainfall_mm,
            "reason": self.reason,
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
        }


class WaNotification(db.Model):
    __tablename__ = "wa_notifications"

    id = db.Column(db.Integer, primary_key=True)
    alert_level_id = db.Column(db.Integer, db.ForeignKey("alert_levels.id", ondelete="CASCADE"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("wa_recipients.id", ondelete="CASCADE"), nullable=False)
    message_body = db.Column(db.Text, nullable=False)
    trigger_type = db.Column(db.Enum("auto", "manual"), default="auto", nullable=False)
    status = db.Column(db.Enum("sent", "failed"), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sent_by = db.Column(db.String(50), nullable=True)  # username petugas jika manual

    recipient = db.relationship("WaRecipient", backref="notifications", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "alert_level_id": self.alert_level_id,
            "recipient_id": self.recipient_id,
            "recipient_name": self.recipient.name if self.recipient else None,
            "recipient_phone": self.recipient.phone_number if self.recipient else None,
            "message_body": self.message_body,
            "trigger_type": self.trigger_type,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "sent_by": self.sent_by,
        }