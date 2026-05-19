from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("operator", "admin", name="user_role"),
        nullable=False,
        default="operator",
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships (untuk keperluan FK di tabel lain)
    alert_configs = db.relationship("AlertConfig", backref="updater", lazy="dynamic")
    notification_configs = db.relationship(
        "NotificationConfig", backref="updater", lazy="dynamic"
    )
    wa_recipients = db.relationship(
        "WaRecipient", backref="adder", lazy="dynamic"
    )

    def set_password(self, password: str) -> None:
        """Hash dan simpan password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifikasi password."""
        return check_password_hash(self.password_hash, password)

    def update_last_login(self) -> None:
        """Perbarui waktu login terakhir."""
        self.last_login = datetime.now(timezone.utc)
        db.session.commit()

    def to_dict(self) -> dict:
        """Serialisasi user (tanpa password_hash)."""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
