from datetime import datetime, timezone
from app import db                         # ← untuk model ini AMAN karena


class SensorReading(db.Model):
    __tablename__ = "sensor_readings"

    id             = db.Column(db.Integer, primary_key=True)
    water_level_cm = db.Column(db.Float, nullable=False)
    temperature_c  = db.Column(db.Float, nullable=True)
    humidity_pct   = db.Column(db.Float, nullable=True)
    sensor_status  = db.Column(
        db.Enum("ONLINE", "DELAY", "OFFLINE"), nullable=False, default="ONLINE"
    )
    recorded_at    = db.Column(db.DateTime, nullable=False)
    received_at    = db.Column(db.DateTime, nullable=False,
                               default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id":             self.id,
            "water_level_cm": self.water_level_cm,
            "temperature_c":  self.temperature_c,
            "humidity_pct":   self.humidity_pct,
            "sensor_status":  self.sensor_status,
            "recorded_at":    self.recorded_at.isoformat() if self.recorded_at else None,
            "received_at":    self.received_at.isoformat() if self.received_at else None,
        }