from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def success_response(data: dict = None, message: str = "Berhasil", status_code: int = 200):
    """Format respons sukses yang konsisten."""
    response = {"status": "success", "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code


def error_response(message: str, error_code: str = None, status_code: int = 400):
    """Format respons error yang konsisten."""
    response = {"status": "error", "message": message}
    if error_code:
        response["error"] = error_code
    return jsonify(response), status_code


def require_role(*roles):
    """
    Decorator untuk membatasi endpoint berdasarkan role.

    Contoh:
        @require_role("admin")
        @require_role("admin", "operator")
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role")
            if user_role not in roles:
                return error_response(
                    "Akses ditolak. Role tidak mencukupi.",
                    error_code="forbidden",
                    status_code=403,
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator
