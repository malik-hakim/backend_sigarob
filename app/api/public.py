"""
app/api/public.py — Blueprint endpoint publik untuk aplikasi Flutter warga
Tidak memerlukan autentikasi JWT.
Semua endpoint READ-ONLY (GET).
"""

from flask import Blueprint, request
from app.utils.responses import success_response, error_response

public_bp = Blueprint("public", __name__)


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/public/status
# Status terkini: level alert, tinggi air, suhu, kelembaban, cuaca
# Digunakan: Beranda Flutter (Hero Card + Quick Info Grid)
# ══════════════════════════════════════════════════════════════════════════════

@public_bp.route("/status", methods=["GET"])
def status():
    from app.models.sensor import SensorReading
    from app.models.alert import AlertLevel
    from app.models.bmkg import BmkgForecast

    sensor  = SensorReading.query.order_by(SensorReading.recorded_at.desc()).first()
    alert   = AlertLevel.query.order_by(AlertLevel.calculated_at.desc()).first()
    bmkg    = BmkgForecast.query.order_by(BmkgForecast.fetched_at.desc()).first()

    if not sensor:
        return error_response("Belum ada data sensor", "NOT_FOUND", 404)

    return success_response({
        # Status utama
        "alert_level":          alert.level if alert else "INFO",
        "flood_probability_24h": alert.flood_probability_24h if alert else None,
        "alert_reason":         alert.reason if alert else None,
        "alert_updated_at":     alert.calculated_at.isoformat() if alert else None,

        # Data sensor
        "water_level_cm":       sensor.water_level_cm,
        "temperature_c":        sensor.temperature_c,
        "humidity_pct":         sensor.humidity_pct,
        "sensor_status":        sensor.sensor_status,
        "sensor_recorded_at":   sensor.recorded_at.isoformat() if sensor.recorded_at else None,

        # Data BMKG
        "weather_desc":         bmkg.weather_desc if bmkg else None,
        "rainfall_mm":          bmkg.rainfall_mm if bmkg else None,
        "wind_speed_kmh":       bmkg.wind_speed_kmh if bmkg else None,
        "wind_direction":       bmkg.wind_direction if bmkg else None,
        "bmkg_updated_at":      bmkg.fetched_at.isoformat() if bmkg else None,
    }, "Status terkini berhasil diambil")


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/public/prakiraan
# Prakiraan 3 hari ke depan berdasarkan prediksi ML + BMKG
# Digunakan: Halaman Prakiraan Flutter
# ══════════════════════════════════════════════════════════════════════════════

@public_bp.route("/prakiraan", methods=["GET"])
def prakiraan():
    from app.models.ml import MlPrediction
    from app.models.alert import AlertLevel
    from app.models.bmkg import BmkgForecast
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)

    # Ambil prediksi terbaru untuk horizon 24, 48, 72 jam
    alert = AlertLevel.query.order_by(AlertLevel.calculated_at.desc()).first()

    def get_pred(horizon_hours):
        if not alert:
            return None
        return MlPrediction.query.filter_by(
            sensor_reading_id=alert.sensor_reading_id,
            horizon_hours=horizon_hours
        ).first()

    pred_24 = get_pred(24)
    pred_48 = get_pred(48)
    pred_72 = get_pred(72)

    # Ambil data BMKG terbaru
    bmkg = BmkgForecast.query.order_by(BmkgForecast.fetched_at.desc()).first()

    def level_dari_prob(prob):
        if prob is None:
            return "INFO"
        if prob >= 0.80:
            return "EVAKUASI"
        if prob >= 0.60:
            return "SIAGA"
        if prob >= 0.40:
            return "WASPADA"
        return "INFO"

    def buat_hari(label, tanggal, prediksi, rainfall_override=None):
        prob = prediksi.flood_probability if prediksi else None
        level = level_dari_prob(prob)
        return {
            "label":              label,
            "date":               tanggal.strftime("%Y-%m-%d"),
            "alert_level":        level,
            "flood_probability":  round(prob, 4) if prob is not None else None,
            "predicted_level_cm": prediksi.predicted_level_cm if prediksi else None,
            "rainfall_mm":        rainfall_override if rainfall_override is not None
                                  else (bmkg.rainfall_mm if bmkg else None),
            "weather_desc":       bmkg.weather_desc if bmkg else None,
            "wind_speed_kmh":     bmkg.wind_speed_kmh if bmkg else None,
        }

    hari_ini  = now
    besok     = now + timedelta(days=1)
    lusa      = now + timedelta(days=2)

    hasil = [
        buat_hari("Hari Ini", hari_ini, pred_24,
                  alert.rainfall_mm if alert else None),
        buat_hari("Besok",    besok,    pred_48),
        buat_hari("Lusa",     lusa,     pred_72),
    ]

    return success_response({
        "days":       hasil,
        "updated_at": now.isoformat(),
        "source":     "Sensor IoT + BMKG Indramayu",
    }, "Prakiraan 3 hari berhasil diambil")


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/public/riwayat
# Riwayat kejadian banjir rob (flood_events)
# Digunakan: Halaman Riwayat Flutter
# ══════════════════════════════════════════════════════════════════════════════

@public_bp.route("/riwayat", methods=["GET"])
def riwayat():
    from app.models.flood_event import FloodEvent
    from app.models.alert import AlertLevel
    from sqlalchemy import func

    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)
    level    = request.args.get("level", "").upper()

    # Query flood_events
    query = FloodEvent.query.order_by(FloodEvent.started_at.desc())
    if level in ("INFO", "WASPADA", "SIAGA", "EVAKUASI"):
        query = query.filter_by(max_level=level)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Statistik ringkas
    total_kejadian = FloodEvent.query.count()
    total_siaga    = FloodEvent.query.filter_by(max_level="SIAGA").count()
    total_evakuasi = FloodEvent.query.filter_by(max_level="EVAKUASI").count()

    return success_response({
        "items": [e.to_dict() for e in pagination.items],
        "total": pagination.total,
        "page":  pagination.page,
        "pages": pagination.pages,
        "stats": {
            "total_kejadian": total_kejadian,
            "total_siaga":    total_siaga,
            "total_evakuasi": total_evakuasi,
        },
    }, "Riwayat banjir rob berhasil diambil")


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/public/panduan
# Titik evakuasi + kontak darurat (untuk halaman Panduan Flutter)
# ══════════════════════════════════════════════════════════════════════════════

@public_bp.route("/panduan", methods=["GET"])
def panduan():
    from app.models.evacuation import EvacuationPoint, EmergencyContact

    titik_evakuasi = (
        EvacuationPoint.query
        .filter_by(is_active=True)
        .order_by(EvacuationPoint.id.asc())
        .all()
    )

    kontak_darurat = (
        EmergencyContact.query
        .filter_by(is_active=True)
        .order_by(EmergencyContact.sort_order.asc(), EmergencyContact.id.asc())
        .all()
    )

    return success_response({
        "evacuation_points":  [t.to_dict() for t in titik_evakuasi],
        "emergency_contacts": [k.to_dict() for k in kontak_darurat],
    }, "Data panduan berhasil diambil")


# ══════════════════════════════════════════════════════════════════════════════
# GET /api/public/riwayat-sensor
# Riwayat 24 jam terakhir (untuk grafik di Flutter jika diperlukan)
# ══════════════════════════════════════════════════════════════════════════════

@public_bp.route("/riwayat-sensor", methods=["GET"])
def riwayat_sensor():
    from app.models.sensor import SensorReading
    from datetime import datetime, timezone, timedelta

    jam = request.args.get("jam", 24, type=int)
    jam = min(jam, 72)  # max 72 jam

    since = datetime.now(timezone.utc) - timedelta(hours=jam)

    readings = (
        SensorReading.query
        .filter(SensorReading.recorded_at >= since)
        .order_by(SensorReading.recorded_at.asc())
        .all()
    )

    return success_response({
        "items": [
            {
                "recorded_at":    r.recorded_at.isoformat() if r.recorded_at else None,
                "water_level_cm": r.water_level_cm,
                "temperature_c":  r.temperature_c,
                "humidity_pct":   r.humidity_pct,
            }
            for r in readings
        ],
        "count":    len(readings),
        "period_h": jam,
    }, f"Riwayat sensor {jam} jam terakhir")
