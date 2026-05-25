"""
PATCH untuk app/services/iot_service.py
Tambahkan trigger prediksi otomatis setelah data sensor masuk.

Ganti seluruh isi file iot_service.py dengan kode ini.
"""

from datetime import datetime, timezone


def simpan_data_sensor(data: dict):
    from app import db
    from app.models.sensor import SensorReading

    temperature = data.get("temperature_c")
    humidity    = data.get("humidity_pct")
    if temperature == -1:
        temperature = None
    if humidity == -1:
        humidity = None

    reading = SensorReading(
        water_level_cm = data["water_level_cm"],
        temperature_c  = temperature,
        humidity_pct   = humidity,
        sensor_status  = data.get("sensor_status", "ONLINE"),
        recorded_at    = data.get("recorded_at") or datetime.now(timezone.utc),
    )

    db.session.add(reading)
    db.session.commit()

    # ── Trigger prediksi otomatis ─────────────────────────────────────────────
    # Dijalankan di background thread agar tidak memperlambat response IoT
    import threading
    t = threading.Thread(
        target=_jalankan_prediksi_background,
        args=(reading.id,),
        daemon=True
    )
    t.start()

    return reading


def _jalankan_prediksi_background(sensor_reading_id: int):
    """
    Jalankan prediksi di background thread.
    Error ditangkap dan di-log, tidak mempengaruhi response sensor.
    """
    try:
        from app.services.ml_service import jalankan_prediksi
        hasil = jalankan_prediksi(sensor_reading_id)
        print(
            f"[ML] Prediksi selesai — "
            f"Air: {hasil['water_level_cm']}cm | "
            f"Prob: {hasil['flood_probability']:.2f} | "
            f"Level: {hasil['alert_level']}"
        )
    except Exception as e:
        print(f"[ML ERROR] Gagal prediksi untuk reading {sensor_reading_id}: {e}")
