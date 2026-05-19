"""
app/api/alert.py — Blueprint Manajemen Alert
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models.alert import AlertLevel, WaNotification
from app.models.config import WaRecipient
from app.models.wa_template import WaTemplate
from app.models.user import User
from app.services import wa_service
from app.utils.responses import success_response, error_response, require_role

alert_bp = Blueprint("alert", __name__)

VALID_LEVELS = ("INFO", "WASPADA", "SIAGA", "EVAKUASI")


# ══════════════════════════════════════════════════════════════════════════════
# BROWSER WHATSAPP WEB
# ══════════════════════════════════════════════════════════════════════════════

@alert_bp.route("/wa/buka", methods=["POST"])
@jwt_required()
def wa_buka():
    status = wa_service.buka_browser()
    return success_response({"status": status}, "Browser sedang dibuka")


@alert_bp.route("/wa/status", methods=["GET"])
@jwt_required()
def wa_status():
    status = wa_service.cek_status()
    return success_response({"status": status}, "Status browser WA")


@alert_bp.route("/wa/tutup", methods=["POST"])
@jwt_required()
@require_role("admin")
def wa_tutup():
    wa_service.tutup_browser()
    return success_response(None, "Browser berhasil ditutup")


@alert_bp.route("/wa/reset", methods=["POST"])
@jwt_required()
@require_role("admin")
def wa_reset():
    wa_service.reset_sesi()
    return success_response(None, "Sesi dihapus. Buka browser kembali untuk scan QR.")


# ══════════════════════════════════════════════════════════════════════════════
# TEMPLATE PESAN
# ══════════════════════════════════════════════════════════════════════════════

@alert_bp.route("/template", methods=["GET"])
@jwt_required()
def get_templates():
    templates = WaTemplate.query.order_by(
        db.case(
            (WaTemplate.level == "INFO", 1),
            (WaTemplate.level == "WASPADA", 2),
            (WaTemplate.level == "SIAGA", 3),
            (WaTemplate.level == "EVAKUASI", 4),
        )
    ).all()
    return success_response(
        {"items": [t.to_dict() for t in templates]},
        "Daftar template WA",
    )


@alert_bp.route("/template/<level>", methods=["GET"])
@jwt_required()
def get_template(level):
    level = level.upper()
    if level not in VALID_LEVELS:
        return error_response("Level tidak valid", status_code=400)

    tmpl = WaTemplate.query.filter_by(level=level).first()
    if not tmpl:
        return error_response("Template tidak ditemukan", status_code=404)

    return success_response(tmpl.to_dict(), f"Template level {level}")


@alert_bp.route("/template/<level>", methods=["PUT"])
@jwt_required()
@require_role("admin")
def update_template(level):
    level = level.upper()
    if level not in VALID_LEVELS:
        return error_response("Level tidak valid", status_code=400)

    data = request.get_json(silent=True) or {}
    template_body = (data.get("template_body") or "").strip()

    if not template_body:
        return error_response("template_body wajib diisi", status_code=400)

    user_id = get_jwt_identity()
    tmpl = WaTemplate.query.filter_by(level=level).first()

    if not tmpl:
        tmpl = WaTemplate(level=level, template_body=template_body, updated_by=user_id)
        db.session.add(tmpl)
    else:
        tmpl.template_body = template_body
        tmpl.updated_by = user_id

    db.session.commit()
    return success_response(tmpl.to_dict(), f"Template {level} berhasil diperbarui")


# ══════════════════════════════════════════════════════════════════════════════
# KIRIM NOTIFIKASI MANUAL
# ══════════════════════════════════════════════════════════════════════════════

@alert_bp.route("/notifikasi/preview", methods=["GET"])
@jwt_required()
def preview_pesan():
    level = (request.args.get("level") or "").upper()
    if level not in VALID_LEVELS:
        return error_response("Level tidak valid", status_code=400)

    tmpl = WaTemplate.query.filter_by(level=level).first()
    if not tmpl:
        return error_response("Template tidak ditemukan", status_code=404)

    return success_response(
        {"level": level, "template_body": tmpl.template_body},
        f"Preview template {level}",
    )


@alert_bp.route("/notifikasi/kirim", methods=["POST"])
@jwt_required()
def kirim_notifikasi():
    """
    Body JSON:
      { "level": "SIAGA", "pesan": "teks pesan yang sudah diedit petugas" }
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return error_response("User tidak ditemukan", status_code=401)

    data = request.get_json(silent=True) or {}
    level = (data.get("level") or "").upper()
    pesan = (data.get("pesan") or "").strip()

    if level not in VALID_LEVELS:
        return error_response("Level tidak valid", status_code=400)
    if not pesan:
        return error_response("Pesan tidak boleh kosong", status_code=400)

    hasil = wa_service.kirim_ke_semua(
        level=level,
        pesan=pesan,
        sent_by=user.username,
    )

    if not hasil.get("success"):
        return error_response(hasil.get("error", "Gagal mengirim notifikasi"), status_code=500)

    total = len(hasil["hasil"])
    berhasil = sum(1 for h in hasil["hasil"] if h["success"])

    return success_response(
        {
            "total": total,
            "berhasil": berhasil,
            "gagal": total - berhasil,
            "results": hasil["hasil"],
        },
        f"Notifikasi dikirim: {berhasil}/{total} berhasil",
    )


# ══════════════════════════════════════════════════════════════════════════════
# RIWAYAT LOG
# ══════════════════════════════════════════════════════════════════════════════

@alert_bp.route("/log/alert", methods=["GET"])
@jwt_required()
def log_alert():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    level_filter = request.args.get("level", "").upper()

    query = AlertLevel.query.order_by(AlertLevel.calculated_at.desc())
    if level_filter in VALID_LEVELS:
        query = query.filter_by(level=level_filter)

    paginasi = query.paginate(page=page, per_page=per_page, error_out=False)

    return success_response(
        {
            "items": [a.to_dict() for a in paginasi.items],
            "total": paginasi.total,
            "page": page,
            "per_page": per_page,
            "total_pages": paginasi.pages,
        },
        "Riwayat alert level",
    )


@alert_bp.route("/log/notifikasi", methods=["GET"])
@jwt_required()
def log_notifikasi():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status_filter = request.args.get("status", "")

    query = WaNotification.query.order_by(WaNotification.sent_at.desc())
    if status_filter in ("sent", "failed"):
        query = query.filter_by(status=status_filter)

    paginasi = query.paginate(page=page, per_page=per_page, error_out=False)

    return success_response(
        {
            "items": [n.to_dict() for n in paginasi.items],
            "total": paginasi.total,
            "page": page,
            "per_page": per_page,
            "total_pages": paginasi.pages,
        },
        "Riwayat notifikasi WA",
    )


# ══════════════════════════════════════════════════════════════════════════════
# MANAJEMEN PENERIMA WA
# ══════════════════════════════════════════════════════════════════════════════

@alert_bp.route("/penerima", methods=["GET"])
@jwt_required()
def get_penerima():
    penerima = WaRecipient.query.order_by(WaRecipient.created_at.desc()).all()
    return success_response(
        {"items": [p.to_dict() for p in penerima], "total": len(penerima)},
        "Daftar penerima WA",
    )


@alert_bp.route("/penerima", methods=["POST"])
@jwt_required()
@require_role("admin")
def tambah_penerima():
    user_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone_number") or "").strip()

    if not name:
        return error_response("Nama wajib diisi", status_code=400)
    if not phone:
        return error_response("Nomor WhatsApp wajib diisi", status_code=400)

    phone_bersih = phone.replace("+", "").replace(" ", "").replace("-", "")
    if phone_bersih.startswith("0"):
        phone_bersih = "62" + phone_bersih[1:]
    elif not phone_bersih.startswith("62"):
        phone_bersih = "62" + phone_bersih

    if WaRecipient.query.filter_by(phone_number=phone_bersih).first():
        return error_response("Nomor sudah terdaftar", "nomor_duplikat", status_code=409)

    penerima = WaRecipient(name=name, phone_number=phone_bersih, added_by=user_id)
    db.session.add(penerima)
    db.session.commit()

    return success_response(penerima.to_dict(), "Penerima berhasil ditambahkan"), 201


@alert_bp.route("/penerima/<int:penerima_id>", methods=["PATCH"])
@jwt_required()
@require_role("admin")
def toggle_penerima(penerima_id):
    penerima = WaRecipient.query.get_or_404(penerima_id)
    data = request.get_json(silent=True) or {}

    if "is_active" not in data:
        return error_response("Field is_active wajib diisi", status_code=400)

    penerima.is_active = bool(data["is_active"])
    db.session.commit()

    status_str = "diaktifkan" if penerima.is_active else "dinonaktifkan"
    return success_response(penerima.to_dict(), f"Penerima berhasil {status_str}")


@alert_bp.route("/penerima/<int:penerima_id>", methods=["DELETE"])
@jwt_required()
@require_role("admin")
def hapus_penerima(penerima_id):
    penerima = WaRecipient.query.get_or_404(penerima_id)
    nama = penerima.name
    db.session.delete(penerima)
    db.session.commit()
    return success_response(None, f"Penerima '{nama}' berhasil dihapus")