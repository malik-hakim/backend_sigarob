"""
app/api/ml.py — Blueprint Prediksi ML
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.utils.responses import success_response, error_response

ml_bp = Blueprint("ml", __name__)


# GET /api/ml/latest — prediksi terbaru
@ml_bp.route("/latest", methods=["GET"])
@jwt_required()
def latest():
    from app.models.alert import AlertLevel
    from app.models.ml import MlPrediction

    alert = AlertLevel.query.order_by(AlertLevel.calculated_at.desc()).first()
    if not alert:
        return error_response("Belum ada data prediksi", "NOT_FOUND", 404)

    # Ambil semua prediksi horizon untuk sensor reading yang sama
    predictions = (
        MlPrediction.query
        .filter_by(sensor_reading_id=alert.sensor_reading_id)
        .order_by(MlPrediction.horizon_hours.asc())
        .all()
    )

    return success_response({
        "alert"      : alert.to_dict(),
        "predictions": [p.to_dict() for p in predictions],
    }, "Prediksi terbaru")


# GET /api/ml/history — riwayat prediksi dengan paginasi
@ml_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    from app.models.ml import MlPrediction

    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    horizon  = request.args.get("horizon", 24, type=int)

    if horizon not in [6, 12, 24, 48, 72]:
        return error_response("horizon harus 6, 12, 24, 48, atau 72", status_code=400)

    pagination = (
        MlPrediction.query
        .filter_by(horizon_hours=horizon)
        .order_by(MlPrediction.predicted_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return success_response({
        "items"   : [p.to_dict() for p in pagination.items],
        "total"   : pagination.total,
        "page"    : pagination.page,
        "pages"   : pagination.pages,
        "horizon" : horizon,
    }, f"Riwayat prediksi horizon {horizon} jam")


# POST /api/ml/predict — trigger prediksi manual berdasarkan sensor reading
@ml_bp.route("/predict", methods=["POST"])
@jwt_required()
def predict_manual():
    from app.services.ml_service import jalankan_prediksi
    from app.models.sensor import SensorReading

    data = request.get_json(silent=True) or {}
    sensor_reading_id = data.get("sensor_reading_id")

    # Jika tidak ada ID, pakai reading terbaru
    if not sensor_reading_id:
        reading = SensorReading.query.order_by(
            SensorReading.recorded_at.desc()
        ).first()
        if not reading:
            return error_response("Belum ada data sensor", "NOT_FOUND", 404)
        sensor_reading_id = reading.id

    try:
        hasil = jalankan_prediksi(sensor_reading_id)
        return success_response(hasil, "Prediksi berhasil dihitung")
    except ValueError as e:
        return error_response(str(e), status_code=404)
    except Exception as e:
        return error_response(f"Gagal prediksi: {str(e)}", "PREDICT_ERROR", 500)


# GET /api/ml/stats — statistik prediksi
@ml_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    from app.models.alert import AlertLevel
    from app import db

    total = AlertLevel.query.count()
    if total == 0:
        return error_response("Belum ada data prediksi", "NOT_FOUND", 404)

    # Hitung distribusi level
    from sqlalchemy import func
    distribusi = db.session.query(
        AlertLevel.level,
        func.count(AlertLevel.id).label("jumlah")
    ).group_by(AlertLevel.level).all()

    dist_dict = {row.level: row.jumlah for row in distribusi}

    # Rata-rata probabilitas banjir 24 jam
    avg_prob = db.session.query(
        func.avg(AlertLevel.flood_probability_24h)
    ).scalar() or 0.0

    return success_response({
        "total_prediksi"        : total,
        "distribusi_level"      : dist_dict,
        "rata_rata_probabilitas": round(float(avg_prob), 4),
    }, "Statistik prediksi")
