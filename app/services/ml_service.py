"""
app/services/ml_service.py
Rule-based scoring untuk prediksi probabilitas banjir rob.

Pendekatan: Expert system berbasis domain knowledge BMKG & sensor IoT.
Rencana upgrade ke model ML (XGBoost) ketika data historis sudah terkumpul.

Formula:
  flood_probability = bobot_air(40%) + bobot_laju(35%) + bobot_hujan(25%)
  + bonus faktor pendukung (angin laut, kelembaban tinggi, jam pasang)

Catatan prototype (skema 50cm):
  - Sensor dipasang 50cm dari dasar wadah
  - Range air efektif: 0-25cm
  - Threshold disesuaikan ke skala prototype
"""

from datetime import datetime, timezone


# ── Threshold ketinggian air (cm) — skala prototype ──────────────────────────
THRESHOLD_WATER = {
    "INFO"     : 5.0,    # air mulai naik dari normal
    "WASPADA"  : 10.0,   # waspada
    "SIAGA"    : 20.0,   # siaga
    "EVAKUASI" : 25.0,   # evakuasi — batas maksimal prototype
}

# ── Threshold probabilitas ────────────────────────────────────────────────────
THRESHOLD_PROB = {
    "INFO"     : 0.20,
    "WASPADA"  : 0.40,
    "SIAGA"    : 0.60,
    "EVAKUASI" : 0.80,
}

# ── Threshold curah hujan (mm) ────────────────────────────────────────────────
THRESHOLD_RAIN = {
    "WASPADA"  : 20.0,
    "SIAGA"    : 40.0,
    "EVAKUASI" : 60.0,
}

# Jam pasang surut rob (puncak biasanya pagi & sore)
JAM_PASANG = [5, 6, 7, 17, 18, 19]

# Bulan musim hujan/rob Indramayu
BULAN_RAWAN = [11, 12, 1, 2, 3]

# ── Konstanta normalisasi prototype ──────────────────────────────────────────
MAX_WATER_LEVEL  = 25.0   # cm — maksimal air prototype
MAX_WATER_RATE   = 2.0    # cm/menit — laju kenaikan max prototype (lebih realistis)
MAX_RAINFALL     = 80.0   # mm — curah hujan maksimal normalisasi


def _hitung_laju_kenaikan(sensor_reading_id: int) -> float:
    """
    Hitung laju kenaikan air (cm/menit) dari 6 reading terakhir.
    Return 0.0 jika data tidak cukup.
    """
    from app.models.sensor import SensorReading

    readings = (
        SensorReading.query
        .order_by(SensorReading.recorded_at.desc())
        .limit(6)
        .all()
    )

    if len(readings) < 2:
        return 0.0

    newest = readings[0]
    oldest = readings[-1]

    delta_level = newest.water_level_cm - oldest.water_level_cm
    delta_time  = (
        newest.recorded_at - oldest.recorded_at
    ).total_seconds() / 60.0

    if delta_time <= 0:
        return 0.0

    return round(delta_level / delta_time, 3)


def _normalisasi(nilai: float, min_val: float, max_val: float) -> float:
    """Normalisasi nilai ke rentang 0.0–1.0."""
    if max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (nilai - min_val) / (max_val - min_val)))


def hitung_flood_probability(
    water_level_cm: float,
    water_level_rate: float,
    rainfall_mm: float,
    wind_speed_kmh: float = 0.0,
    wind_direction: str = "",
    humidity_pct: float = 0.0,
    hour_of_day: int = None,
    month: int = None,
) -> dict:
    """
    Hitung probabilitas banjir rob menggunakan rule-based scoring.

    Args:
        water_level_cm   : Ketinggian air saat ini (0–25 cm prototype)
        water_level_rate : Laju kenaikan air (cm/menit), bisa negatif
        rainfall_mm      : Curah hujan prakiraan dari BMKG (mm)
        wind_speed_kmh   : Kecepatan angin (km/h)
        wind_direction   : Arah angin (string, misal "N", "NE", "NW")
        humidity_pct     : Kelembaban udara (%)
        hour_of_day      : Jam saat ini (0–23)
        month            : Bulan saat ini (1–12)

    Returns:
        dict berisi flood_probability, skor tiap komponen, dan detail reasoning
    """
    now = datetime.now(timezone.utc)
    if hour_of_day is None:
        hour_of_day = now.hour
    if month is None:
        month = now.month

    # ── Komponen 1: Ketinggian air (bobot 40%) ────────────────────────────────
    # Normalisasi: 0cm = 0.0, 25cm = 1.0 (disesuaikan prototype)
    skor_air = _normalisasi(water_level_cm, 0, MAX_WATER_LEVEL)

    # ── Komponen 2: Laju kenaikan air (bobot 35%) ─────────────────────────────
    # Normalisasi: 0 cm/menit = 0.0, 2 cm/menit = 1.0 (disesuaikan prototype)
    # Laju negatif (air turun) = 0
    skor_laju = _normalisasi(max(0, water_level_rate), 0, MAX_WATER_RATE)

    # ── Komponen 3: Curah hujan BMKG (bobot 25%) ──────────────────────────────
    # Normalisasi: 0mm = 0.0, 80mm = 1.0
    skor_hujan = _normalisasi(rainfall_mm, 0, MAX_RAINFALL)

    # ── Skor dasar (weighted sum) ─────────────────────────────────────────────
    skor_dasar = (
        skor_air   * 0.40 +
        skor_laju  * 0.35 +
        skor_hujan * 0.25
    )

    # ── Bonus faktor pendukung (maksimal +0.20) ───────────────────────────────
    bonus = 0.0

    # Angin dari laut (utara / timur laut / barat laut)
    arah_laut = {"N", "NE", "NW", "UTARA", "TIMUR LAUT", "BARAT LAUT"}
    if wind_direction.upper().strip() in arah_laut:
        bonus += 0.05

    # Angin kencang
    if wind_speed_kmh >= 40:
        bonus += 0.05
    elif wind_speed_kmh >= 25:
        bonus += 0.02

    # Kelembaban tinggi
    if humidity_pct >= 90:
        bonus += 0.04
    elif humidity_pct >= 80:
        bonus += 0.02

    # Jam pasang surut
    if hour_of_day in JAM_PASANG:
        bonus += 0.03

    # Musim hujan / bulan rawan
    if month in BULAN_RAWAN:
        bonus += 0.03

    bonus = min(bonus, 0.20)

    # ── Probabilitas akhir ────────────────────────────────────────────────────
    flood_probability = round(min(1.0, skor_dasar + bonus), 4)

    # ── Reasoning teks ───────────────────────────────────────────────────────
    parts = []
    parts.append(f"Air {water_level_cm:.1f}cm (skor:{skor_air:.2f})")
    parts.append(f"Laju {water_level_rate:+.2f}cm/mnt (skor:{skor_laju:.2f})")
    parts.append(f"Hujan {rainfall_mm:.1f}mm (skor:{skor_hujan:.2f})")
    if bonus > 0:
        parts.append(f"Bonus faktor pendukung: +{bonus:.2f}")
    reason = " | ".join(parts)

    return {
        "flood_probability" : flood_probability,
        "skor_air"          : round(skor_air, 4),
        "skor_laju"         : round(skor_laju, 4),
        "skor_hujan"        : round(skor_hujan, 4),
        "bonus"             : round(bonus, 4),
        "water_level_rate"  : water_level_rate,
        "reason"            : reason,
    }


def tentukan_alert_level(
    water_level_cm: float,
    flood_probability: float,
    rainfall_mm: float,
) -> str:
    """
    Tentukan level alert berdasarkan kombinasi 3 parameter.
    Menggunakan logika OR — cukup satu parameter memenuhi syarat.

    Returns: "INFO" | "WASPADA" | "SIAGA" | "EVAKUASI"
    """
    # Cek dari level tertinggi ke terendah
    if (water_level_cm   >= THRESHOLD_WATER["EVAKUASI"] or
            flood_probability >= THRESHOLD_PROB["EVAKUASI"] or
            rainfall_mm       >= THRESHOLD_RAIN["EVAKUASI"]):
        return "EVAKUASI"

    if (water_level_cm   >= THRESHOLD_WATER["SIAGA"] or
            flood_probability >= THRESHOLD_PROB["SIAGA"] or
            rainfall_mm       >= THRESHOLD_RAIN["SIAGA"]):
        return "SIAGA"

    if (water_level_cm   >= THRESHOLD_WATER["WASPADA"] or
            flood_probability >= THRESHOLD_PROB["WASPADA"] or
            rainfall_mm       >= THRESHOLD_RAIN["WASPADA"]):
        return "WASPADA"

    return "INFO"


def jalankan_prediksi(sensor_reading_id: int) -> dict:
    """
    Entry point utama — dipanggil setiap kali data sensor masuk.

    1. Ambil data sensor terbaru
    2. Ambil data BMKG terbaru
    3. Hitung laju kenaikan air dari 6 reading terakhir
    4. Hitung flood_probability
    5. Simpan ke ml_predictions (semua horizon: 6,12,24,48,72 jam)
    6. Hitung & simpan alert_level ke DB
    7. Return hasil lengkap

    Args:
        sensor_reading_id: ID dari SensorReading yang baru masuk

    Returns:
        dict berisi prediksi lengkap dan alert level
    """
    from app import db
    from app.models.sensor import SensorReading
    from app.models.bmkg import BmkgForecast
    from app.models.ml import MlPrediction
    from app.models.alert import AlertLevel

    # ── 1. Ambil data sensor ──────────────────────────────────────────────────
    reading = SensorReading.query.get(sensor_reading_id)
    if not reading:
        raise ValueError(f"SensorReading id={sensor_reading_id} tidak ditemukan")

    # ── 2. Ambil data BMKG terbaru ────────────────────────────────────────────
    bmkg = BmkgForecast.query.order_by(BmkgForecast.fetched_at.desc()).first()

    rainfall_mm    = bmkg.rainfall_mm    if bmkg else 0.0
    wind_speed_kmh = bmkg.wind_speed_kmh if bmkg else 0.0
    wind_direction = bmkg.wind_direction if bmkg else ""
    humidity_bmkg  = bmkg.humidity_pct   if bmkg else 0.0
    bmkg_id        = bmkg.id             if bmkg else None

    # Jika tidak ada BMKG, gunakan humidity dari sensor
    humidity = humidity_bmkg or reading.humidity_pct or 0.0

    # ── 3. Hitung laju kenaikan air ───────────────────────────────────────────
    water_level_rate = _hitung_laju_kenaikan(sensor_reading_id)

    # ── 4. Hitung flood probability ───────────────────────────────────────────
    hasil = hitung_flood_probability(
        water_level_cm   = reading.water_level_cm,
        water_level_rate = water_level_rate,
        rainfall_mm      = rainfall_mm,
        wind_speed_kmh   = wind_speed_kmh or 0.0,
        wind_direction   = wind_direction or "",
        humidity_pct     = humidity,
        hour_of_day      = reading.recorded_at.hour,
        month            = reading.recorded_at.month,
    )

    flood_prob = hasil["flood_probability"]

    # ── 5. Simpan ml_predictions untuk semua horizon ──────────────────────────
    HORIZONS = [6, 12, 24, 48, 72]
    predictions = []

    for horizon in HORIZONS:
        # Faktor decay: makin jauh horizon, makin tidak pasti
        decay = {6: 1.0, 12: 0.95, 24: 0.88, 48: 0.78, 72: 0.70}[horizon]
        prob_horizon = round(flood_prob * decay, 4)

        pred = MlPrediction(
            sensor_reading_id  = sensor_reading_id,
            bmkg_forecast_id   = bmkg_id,
            horizon_hours      = horizon,
            predicted_level_cm = reading.water_level_cm,
            flood_probability  = prob_horizon,
        )
        db.session.add(pred)
        predictions.append(pred)

    db.session.flush()

    # ── 6. Hitung & simpan alert_level ───────────────────────────────────────
    alert_level_str = tentukan_alert_level(
        water_level_cm    = reading.water_level_cm,
        flood_probability = flood_prob,
        rainfall_mm       = rainfall_mm,
    )

    pred_24h = next((p for p in predictions if p.horizon_hours == 24), predictions[0])

    alert = AlertLevel(
        sensor_reading_id     = sensor_reading_id,
        ml_prediction_id      = pred_24h.id,
        level                 = alert_level_str,
        water_level_cm        = reading.water_level_cm,
        flood_probability_24h = pred_24h.flood_probability,
        rainfall_mm           = rainfall_mm,
        reason                = f"{alert_level_str}: {hasil['reason']}",
    )
    db.session.add(alert)
    db.session.commit()

    return {
        "sensor_reading_id" : sensor_reading_id,
        "water_level_cm"    : reading.water_level_cm,
        "water_level_rate"  : water_level_rate,
        "flood_probability" : flood_prob,
        "alert_level"       : alert_level_str,
        "rainfall_mm"       : rainfall_mm,
        "reason"            : hasil["reason"],
        "predictions"       : [
            {
                "horizon_hours"    : p.horizon_hours,
                "flood_probability": p.flood_probability,
                "id"               : p.id,
            }
            for p in predictions
        ],
        "alert_level_id"    : alert.id,
        "bmkg_tersedia"     : bmkg is not None,
    }