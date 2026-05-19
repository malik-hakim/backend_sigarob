from datetime import datetime, timezone
from typing import Optional

from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)

from app import db
from app.models.user import User


class AuthService:
    """Service layer untuk autentikasi — pisahkan logika bisnis dari API layer."""

    @staticmethod
    def login(username: str, password: str) -> dict:
        """
        Validasi kredensial dan buat token JWT.

        Returns:
            dict berisi access_token, refresh_token, dan data user.

        Raises:
            ValueError: Jika kredensial salah atau akun nonaktif.
        """
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            raise ValueError("Username atau password salah.")

        if not user.is_active:
            raise ValueError("Akun Anda dinonaktifkan. Hubungi administrator.")

        # Update last_login
        user.update_last_login()

        # Buat token dengan identity = user id, dan role sebagai additional claims
        identity = str(user.id)
        additional_claims = {"role": user.role, "username": user.username}

        access_token = create_access_token(
            identity=identity, additional_claims=additional_claims
        )
        refresh_token = create_refresh_token(
            identity=identity, additional_claims=additional_claims
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
        }

    @staticmethod
    def refresh_access_token(user_id: str) -> dict:
        """Buat access token baru dari refresh token yang valid."""
        user = User.query.get(int(user_id))

        if user is None or not user.is_active:
            raise ValueError("User tidak ditemukan atau nonaktif.")

        additional_claims = {"role": user.role, "username": user.username}
        access_token = create_access_token(
            identity=user_id, additional_claims=additional_claims
        )

        return {"access_token": access_token}

    @staticmethod
    def get_current_user(user_id: str) -> Optional[User]:
        """Ambil data user berdasarkan ID dari JWT identity."""
        try:
            return User.query.get(int(user_id))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> None:
        """
        Ganti password user setelah memverifikasi password lama.

        Raises:
            ValueError: Jika password lama salah atau validasi gagal.
        """
        user = User.query.get(user_id)
        if user is None:
            raise ValueError("User tidak ditemukan.")

        if not user.check_password(old_password):
            raise ValueError("Password lama tidak sesuai.")

        if len(new_password) < 8:
            raise ValueError("Password baru minimal 8 karakter.")

        user.set_password(new_password)
        db.session.commit()
