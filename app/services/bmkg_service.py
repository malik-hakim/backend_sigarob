import requests
from datetime import datetime, timezone
from app import db

BMKG_ADM4 = "32.12.21.2011"  # Sesuaikan dengan kode wilayah sensor
BMKG_URL  = f"https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={BMKG_ADM4}"


def fetch_dan_simpan_bmkg() -> dict:
    """
    Fetch prakiraan cuaca BMKG, simpan periode terdekat ke tabel bmkg_forecasts.
    """
    from app.models.bmkg import BmkgForecast

    # ── 1. Request ke API BMKG dengan User-Agent ──
    try:
        resp = requests.get(
            BMKG_URL,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; SIGAP/1.0)",
                "Accept": "application/json",
            }
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as e:
        raise Exception(f"Gagal fetch BMKG: {str(e)}")

    # ── 2. Navigasi struktur JSON BMKG ──
    try:
        cuaca_nested = payload["data"][0]["cuaca"]
        all_periods  = [item for sublist in cuaca_nested for item in sublist]
    except (KeyError, IndexError, TypeError) as e:
        raise Exception(f"Struktur respons BMKG tidak dikenali: {str(e)}")

    if not all_periods:
        raise Exception("Tidak ada data cuaca dari BMKG")

    # ── 3. Parse datetime — handle format BMKG "2026-05-08 19:00:00" (spasi) ──
    def parse_dt(period):
        raw = period.get("local_datetime") or period.get("utc_datetime") or ""
        try:
            raw = raw.strip().replace("Z", "+00:00")
            if "T" not in raw and " " in raw:
                raw = raw.replace(" ", "T") + "+07:00"  # WIB = UTC+7
            return datetime.fromisoformat(raw)
        except Exception:
            return None

    # ── 4. Pilih periode terdekat dengan waktu sekarang ──
    now   = datetime.now(timezone.utc)
    valid = [(p, parse_dt(p)) for p in all_periods if parse_dt(p)]

    if not valid:
        raise Exception("Tidak ada periode waktu valid dari BMKG")

    closest_period, closest_dt = min(
        valid,
        key=lambda x: abs((x[1] - now).total_seconds())
    )

    # ── 5. Ekstrak field ──
    rainfall_mm  = float(closest_period.get("tp",  0) or 0)
    humidity_pct = float(closest_period.get("hu",  0) or 0) or None
    wind_speed   = float(closest_period.get("ws",  0) or 0) or None  # sudah km/h
    wind_dir     = str(closest_period.get("wd_to", "") or "")[:10] or None
    weather_desc = str(closest_period.get("weather_desc", "") or "")[:100] or None

    # ── 6. Simpan ke DB ──
    record = BmkgForecast(
        rainfall_mm    = rainfall_mm,
        wind_speed_kmh = wind_speed,
        wind_direction = wind_dir,
        humidity_pct   = humidity_pct,
        weather_desc   = weather_desc,
        forecast_time  = closest_dt,
    )

    db.session.add(record)
    db.session.commit()
    return record.to_dict()


def get_latest_bmkg() -> dict | None:
    """Ambil data BMKG terbaru dari DB."""
    from app.models.bmkg import BmkgForecast
    record = BmkgForecast.query.order_by(BmkgForecast.fetched_at.desc()).first()
    return record.to_dict() if record else None