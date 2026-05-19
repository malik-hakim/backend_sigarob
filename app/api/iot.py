from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.utils.responses import success_response, error_response
from marshmallow import ValidationError

iot_bp = Blueprint("iot", __name__, url_prefix="/api/iot")


@iot_bp.route("/data", methods=["POST"])
def terima_data_sensor():
    from flask import current_app
    from app.services.iot_service import simpan_data_sensor   # ← lazy import
    from app.utils.validators import SensorReadingSchema

    expected_key = current_app.config.get("IOT_API_KEY", "")
    api_key = request.headers.get("X-API-Key", "")
    if not api_key or api_key != expected_key:
        return error_response("API key tidak valid", "UNAUTHORIZED", 401)

    json_data = request.get_json(silent=True)
    if not json_data:
        return error_response("Body JSON kosong atau tidak valid", "INVALID_JSON", 400)

    schema = SensorReadingSchema()
    try:
        data = schema.load(json_data)
    except ValidationError:
        return error_response("Data tidak valid", "VALIDATION_ERROR", 400)

    try:
        reading = simpan_data_sensor(data)
        return success_response(reading.to_dict(), "Data sensor berhasil disimpan", 201)
    except Exception as e:
        return error_response(f"Gagal menyimpan: {str(e)}", "DB_ERROR", 500)


@iot_bp.route("/latest", methods=["GET"])
@jwt_required()
def data_terbaru():
    from app.models.sensor import SensorReading   # ← lazy import

    reading = SensorReading.query.order_by(SensorReading.recorded_at.desc()).first()
    if not reading:
        return error_response("Belum ada data sensor", "NOT_FOUND", 404)
    return success_response(reading.to_dict(), "Data sensor terbaru")


@iot_bp.route("/history", methods=["GET"])
@jwt_required()
def riwayat_sensor():
    from app.models.sensor import SensorReading   # ← lazy import

    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)

    pagination = (
        SensorReading.query
        .order_by(SensorReading.recorded_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return success_response({
        "items":    [r.to_dict() for r in pagination.items],
        "total":    pagination.total,
        "page":     pagination.page,
        "pages":    pagination.pages,
        "per_page": pagination.per_page,
    }, "Riwayat data sensor")