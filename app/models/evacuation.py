"""
app/models/evacuation.py — Model titik evakuasi & kontak darurat
"""
from datetime import datetime, timezone
from app import db


class EvacuationPoint(db.Model):
    __tablename__ = "evacuation_points"

    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name        = db.Column(db.String(100), nullable=False)
    address     = db.Column(db.String(255), nullable=False)
    latitude    = db.Column(db.Float, nullable=False)
    longitude   = db.Column(db.Float, nullable=False)
    capacity    = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text, nullable=True)
    is_active   = db.Column(db.Boolean, nullable=False, default=True)
    created_by  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at  = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at  = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "address":     self.address,
            "latitude":    self.latitude,
            "longitude":   self.longitude,
            "capacity":    self.capacity,
            "description": self.description,
            "is_active":   self.is_active,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
            "updated_at":  self.updated_at.isoformat() if self.updated_at else None,
        }


class EmergencyContact(db.Model):
    __tablename__ = "emergency_contacts"

    VALID_CATEGORIES = (
        "BPBD", "BASARNAS", "POLSEK_KORAMIL", "PMI", "PUSKESMAS", "LAINNYA"
    )

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name         = db.Column(db.String(100), nullable=False)
    category     = db.Column(
        db.Enum("BPBD", "BASARNAS", "POLSEK_KORAMIL", "PMI", "PUSKESMAS", "LAINNYA"),
        nullable=False, default="LAINNYA"
    )
    phone_number = db.Column(db.String(20), nullable=False)
    address      = db.Column(db.String(255), nullable=True)
    description  = db.Column(db.String(255), nullable=True)
    is_active    = db.Column(db.Boolean, nullable=False, default=True)
    sort_order   = db.Column(db.Integer, nullable=False, default=0)
    created_by   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at   = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at   = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "name":         self.name,
            "category":     self.category,
            "phone_number": self.phone_number,
            "address":      self.address,
            "description":  self.description,
            "is_active":    self.is_active,
            "sort_order":   self.sort_order,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
        }
