from datetime import datetime, timezone
from app import db


class BmkgForecast(db.Model):
    __tablename__ = "bmkg_forecasts"

    id             = db.Column(db.Integer, primary_key=True)
    rainfall_mm    = db.Column(db.Float, nullable=False, default=0)
    wind_speed_kmh = db.Column(db.Float, nullable=True)
    wind_direction = db.Column(db.String(10), nullable=True)
    humidity_pct   = db.Column(db.Float, nullable=True)
    weather_desc   = db.Column(db.String(100), nullable=True)   # ← field baru
    forecast_time  = db.Column(db.DateTime, nullable=False)
    fetched_at     = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id":             self.id,
            "rainfall_mm":    self.rainfall_mm,
            "wind_speed_kmh": self.wind_speed_kmh,
            "wind_direction": self.wind_direction,
            "humidity_pct":   self.humidity_pct,
            "weather_desc":   self.weather_desc,
            "forecast_time":  self.forecast_time.isoformat() if self.forecast_time else None,
            "fetched_at":     self.fetched_at.isoformat() if self.fetched_at else None,
        }