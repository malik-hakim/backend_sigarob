"""
app/models/flood_event.py — Model riwayat kejadian banjir rob
(Tabel flood_events sudah ada di DB, ini hanya model SQLAlchemy-nya)
"""
from app import db


class FloodEvent(db.Model):
    __tablename__ = "flood_events"

    id                  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    max_level           = db.Column(
        db.Enum("INFO", "WASPADA", "SIAGA", "EVAKUASI"),
        nullable=False
    )
    max_water_level_cm  = db.Column(db.Float, nullable=False)
    started_at          = db.Column(db.DateTime, nullable=False)
    ended_at            = db.Column(db.DateTime, nullable=True)
    # duration_minutes adalah GENERATED COLUMN di MySQL — tidak di-map di ORM
    notes               = db.Column(db.Text, nullable=True)

    @property
    def duration_minutes(self):
        """Hitung durasi di Python (karena GENERATED COLUMN tidak bisa di-read ORM)."""
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    def to_dict(self):
        return {
            "id":                 self.id,
            "max_level":          self.max_level,
            "max_water_level_cm": self.max_water_level_cm,
            "started_at":         self.started_at.isoformat() if self.started_at else None,
            "ended_at":           self.ended_at.isoformat() if self.ended_at else None,
            "duration_minutes":   self.duration_minutes,
            "notes":              self.notes,
        }
