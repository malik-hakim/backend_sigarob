from datetime import datetime, timezone


def simpan_data_sensor(data: dict):
    from app import db                        # ← import di dalam fungsi, bukan di atas
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
    return reading