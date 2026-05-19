from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.services.auth_service import AuthService
from app.utils.responses import success_response, error_response
from app.utils.validators import login_schema, change_password_schema

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /api/auth/login
    Body: { "username": "...", "password": "..." }
    """
    json_data = request.get_json(silent=True)
    if not json_data:
        return error_response("Request body harus JSON.", status_code=400)

    # Validasi input
    try:
        data = login_schema.load(json_data)
    except ValidationError as e:
        return error_response(
            str(list(e.messages.values())[0][0]),
            error_code="validation_error",
            status_code=422,
        )

    # Proses login
    try:
        result = AuthService.login(data["username"], data["password"])
    except ValueError as e:
        return error_response(str(e), error_code="invalid_credentials", status_code=401)

    return success_response(
        data=result,
        message="Login berhasil.",
        status_code=200,
    )


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    POST /api/auth/refresh
    Header: Authorization: Bearer <refresh_token>
    """
    user_id = get_jwt_identity()

    try:
        result = AuthService.refresh_access_token(user_id)
    except ValueError as e:
        return error_response(str(e), error_code="refresh_failed", status_code=401)

    return success_response(data=result, message="Token diperbarui.")


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """
    GET /api/auth/me
    Header: Authorization: Bearer <access_token>
    """
    user_id = get_jwt_identity()
    user = AuthService.get_current_user(user_id)

    if user is None:
        return error_response("User tidak ditemukan.", status_code=404)

    return success_response(data={"user": user.to_dict()})


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    """
    PUT /api/auth/change-password
    Header: Authorization: Bearer <access_token>
    Body: { "old_password": "...", "new_password": "..." }
    """
    json_data = request.get_json(silent=True)
    if not json_data:
        return error_response("Request body harus JSON.", status_code=400)

    try:
        data = change_password_schema.load(json_data)
    except ValidationError as e:
        return error_response(
            str(list(e.messages.values())[0][0]),
            error_code="validation_error",
            status_code=422,
        )

    user_id = int(get_jwt_identity())

    try:
        AuthService.change_password(user_id, data["old_password"], data["new_password"])
    except ValueError as e:
        return error_response(str(e), error_code="change_password_failed", status_code=400)

    return success_response(message="Password berhasil diubah.")


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    POST /api/auth/logout
    Catatan: JWT adalah stateless — logout ditangani di sisi klien
    dengan menghapus token. Endpoint ini hanya konfirmasi.
    (Untuk blacklist token, implementasi bisa ditambahkan di sini.)
    """
    return success_response(message="Logout berhasil. Hapus token di sisi klien.")
