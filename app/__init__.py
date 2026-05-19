from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.config import get_config
from app.api.iot import iot_bp
 

db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())
    app.register_blueprint(iot_bp)

    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=app.config["CORS_ORIGINS"], supports_credentials=True)

    _register_jwt_callbacks(jwt)

    # ← Tambahkan ini
    with app.app_context():
        from app.models import User, AlertConfig, NotificationConfig, WaRecipient

    from app.api.auth import auth_bp
    from app.api.alert import alert_bp
    from app.api.bmkg import bmkg_bp   

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(alert_bp, url_prefix="/api/alert")
    app.register_blueprint(bmkg_bp, url_prefix="/api/bmkg")   # ← Tambahkan ini
   

    from app.commands import register_commands
    register_commands(app)

    return app


def _register_jwt_callbacks(jwt: JWTManager):
    from flask import jsonify

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return jsonify({"error": "token_expired", "message": "Token telah kedaluwarsa"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "token_invalid", "message": "Token tidak valid"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"error": "authorization_required", "message": "Token diperlukan"}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_data):
        return jsonify({"error": "token_revoked", "message": "Token telah dicabut"}), 401