from datetime import datetime
from app import db


class WaTemplate(db.Model):
    __tablename__ = "wa_templates"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    level = db.Column(
        db.Enum("INFO", "WASPADA", "SIAGA", "EVAKUASI"),
        nullable=False,
        unique=True,
    )
    template_body = db.Column(db.Text, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "level": self.level,
            "template_body": self.template_body,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }