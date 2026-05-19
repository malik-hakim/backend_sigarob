"""
wa_service.py — Layanan pengiriman WhatsApp via Selenium (WhatsApp Web)
Notifikasi HANYA dikirim secara manual oleh petugas.
"""

import os
import time
import threading
import urllib.parse

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

_driver = None
_driver_lock = threading.Lock()
_status_login = "belum"  # belum | loading | siap | error:<pesan>


# ─── Status & utilitas driver ─────────────────────────────────────────────────

def cek_status():
    global _status_login
    if _status_login == "siap" and not _is_driver_alive():
        _status_login = "belum"
    return _status_login


def _is_driver_alive():
    global _driver
    if _driver is None:
        return False
    try:
        _ = _driver.current_url
        return True
    except Exception:
        return False


def _buat_options():
    profil_dir = os.path.abspath("./wa_session")
    os.makedirs(profil_dir, exist_ok=True)

    opts = uc.ChromeOptions()
    opts.add_argument(f"--user-data-dir={profil_dir}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-background-networking")
    opts.add_argument("--disable-sync")
    opts.add_argument("--mute-audio")
    opts.add_argument("--window-size=1280,800")
    opts.add_argument("--disable-notifications")
    return opts


def _tutup_driver():
    global _driver, _status_login
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None
    _status_login = "belum"


# ─── Init driver ─────────────────────────────────────────────────────────────

def _init_driver():
    global _driver, _status_login
    _status_login = "loading"
    try:
        print("[WA] Memulai Chrome...")
        _driver = uc.Chrome(
            options=_buat_options(),
            use_subprocess=True,
            version_main=147,
        )
        print("[WA] Chrome terbuka, membuka WA Web...")
        _driver.get("https://web.whatsapp.com")
        _status_login = "siap"
        print("[WA] Siap!")
    except Exception as e:
        print(f"[WA ERROR] {e}")
        _status_login = f"error: {str(e)}"
        _driver = None


def _pastikan_driver_hidup():
    global _driver, _status_login
    if _is_driver_alive():
        return True

    print("[WA] Browser mati, mencoba reconnect...")
    _tutup_driver()
    _status_login = "loading"
    try:
        _driver = uc.Chrome(
            options=_buat_options(),
            use_subprocess=True,
            version_main=147,
        )
        _driver.get("https://web.whatsapp.com")

        for _ in range(20):
            time.sleep(1)
            try:
                if "web.whatsapp.com" in _driver.current_url:
                    try:
                        _driver.find_element(By.XPATH, '//div[@data-testid="chat-list"]')
                        _status_login = "siap"
                        return True
                    except Exception:
                        pass
            except Exception:
                break

        _status_login = "siap"
        return True
    except Exception as e:
        _status_login = f"error: {str(e)}"
        _driver = None
        return False


# ─── Manajemen browser ────────────────────────────────────────────────────────

def buka_browser():
    global _status_login
    if _is_driver_alive() and _status_login == "siap":
        return "siap"
    if _status_login == "loading":
        return "loading"
    _tutup_driver()
    t = threading.Thread(target=_init_driver, daemon=True)
    t.start()
    return "loading"


def tutup_browser():
    _tutup_driver()


def reset_sesi():
    import shutil
    _tutup_driver()
    sesi_dir = os.path.abspath("./wa_session")
    if os.path.exists(sesi_dir):
        shutil.rmtree(sesi_dir, ignore_errors=True)


# ─── Kirim pesan ke satu nomor ────────────────────────────────────────────────

def _kirim_satu(nomor_bersih, pesan, max_retry=2):
    global _driver
    for percobaan in range(max_retry):
        try:
            pesan_enc = urllib.parse.quote(pesan)
            url = f"https://web.whatsapp.com/send?phone={nomor_bersih}&text={pesan_enc}"
            _driver.get(url)
            time.sleep(2.0)

            wait = WebDriverWait(_driver, 20)

            # Cek nomor tidak valid
            try:
                invalid = WebDriverWait(_driver, 4).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        '//*[contains(text(),"phone number shared via url is invalid")]',
                    ))
                )
                if invalid:
                    return False, "Nomor tidak terdaftar di WhatsApp"
            except Exception:
                pass

            # Tunggu kotak input
            kotak = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            ))
            time.sleep(1.0)
            kotak.click()
            time.sleep(0.5)

            kotak.send_keys(" ")
            time.sleep(0.3)
            kotak.send_keys(Keys.BACK_SPACE)
            time.sleep(0.3)
            kotak.send_keys(Keys.ENTER)
            time.sleep(2.0)

            # Verifikasi terkirim
            try:
                WebDriverWait(_driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//span[@data-testid="msg-time"]')
                    )
                )
            except Exception:
                try:
                    tombol = _driver.find_element(
                        By.XPATH, '//button[@data-testid="compose-btn-send"]'
                    )
                    tombol.click()
                    time.sleep(2.0)
                except Exception:
                    pass

            print(f"[WA OK] Terkirim ke {nomor_bersih}")
            return True, ""

        except Exception as e:
            print(f"[WA RETRY {percobaan + 1}] Gagal ke {nomor_bersih}: {e}")
            time.sleep(2.0)
            if percobaan == max_retry - 1:
                return False, str(e)

    return False, "Gagal setelah retry"


# ─── Kirim ke semua penerima aktif ───────────────────────────────────────────

def kirim_ke_semua(level, pesan, sent_by):
    from app import db
    from app.models.config import WaRecipient
    from app.models.alert import WaNotification

    if not _pastikan_driver_hidup():
        return {"success": False, "error": f"Browser tidak aktif: {_status_login}"}

    recipients = WaRecipient.query.filter_by(is_active=True).all()
    if not recipients:
        return {"success": False, "error": "Tidak ada nomor penerima yang aktif"}

    hasil = []

    with _driver_lock:
        for r in recipients:
            if not _is_driver_alive():
                hasil.append({
                    "name": r.name,
                    "phone_number": r.phone_number,
                    "success": False,
                    "error": "Browser tertutup saat pengiriman",
                    "status": "failed",
                })
                _simpan_log(db, r.id, pesan, "failed", sent_by)
                continue

            nomor_bersih = (
                r.phone_number
                .replace("+", "")
                .replace(" ", "")
                .replace("-", "")
            )
            ok, err = _kirim_satu(nomor_bersih, pesan)
            _simpan_log(db, r.id, pesan, "sent" if ok else "failed", sent_by)

            hasil.append({
                "name": r.name,
                "phone_number": r.phone_number,
                "success": ok,
                "error": err,
                "status": "sent" if ok else "failed",
            })

    return {"success": True, "hasil": hasil}


def _simpan_log(db, recipient_id, message_body, status, sent_by):
    from app.models.alert import WaNotification
    try:
        log = WaNotification(
            alert_level_id=None,
            recipient_id=recipient_id,
            message_body=message_body,
            trigger_type="manual",
            status=status,
            sent_by=sent_by,
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"[WA LOG ERROR] {e}")
        db.session.rollback()