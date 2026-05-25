"""
app/models/ml.py — Model tabel ml_predictions
"""
from datetime import datetime, timezone
from app import db


class MlPrediction(db.Model):
    __tablename__ = "ml_predictions"

    id                 = db.Column(db.Integer, primary_key=True)
    sensor_reading_id  = db.Column(
        db.Integer,
        db.ForeignKey("sensor_readings.id", ondelete="CASCADE"),
        nullable=False
    )
    bmkg_forecast_id   = db.Column(
        db.Integer,
        db.ForeignKey("bmkg_forecasts.id", ondelete="CASCADE"),
        nullable=True   # nullable: bisa prediksi tanpa data BMKG
    )
    horizon_hours      = db.Column(db.SmallInteger, nullable=False)  # 6,12,24,48,72
    predicted_level_cm = db.Column(db.Float, nullable=False)
    flood_probability  = db.Column(db.Float, nullable=False)
    predicted_at       = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id"                : self.id,
            "sensor_reading_id" : self.sensor_reading_id,
            "bmkg_forecast_id"  : self.bmkg_forecast_id,
            "horizon_hours"     : self.horizon_hours,
            "predicted_level_cm": self.predicted_level_cm,
            "flood_probability" : self.flood_probability,
            "predicted_at"      : self.predicted_at.isoformat() if self.predicted_at else None,
        }
