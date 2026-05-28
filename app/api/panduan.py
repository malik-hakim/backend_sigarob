"""
app/api/panduan.py — Blueprint admin untuk manajemen titik evakuasi & kontak darurat
Endpoint ini memerlukan autentikasi JWT + role admin.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.utils.responses import success_response, error_response, require_role

panduan_bp = Blueprint("panduan", __name__)


# ══════════════════════════════════════════════════════════════════════════════
# TITIK EVAKUASI (CRUD — admin only untuk CUD)
# ══════════════════════════════════════════════════════════════════════════════

@panduan_bp.route("/evakuasi", methods=["GET"])
@jwt_required()
def list_evakuasi():
    """GET /api/panduan/evakuasi — daftar semua titik evakuasi (termasuk nonaktif)."""
    from app.models.evacuation import EvacuationPoint

    hanya_aktif = request.args.get("aktif", "0") == "1"
    query = EvacuationPoint.query.order_by(EvacuationPoint.id.asc())
    if hanya_aktif:
        query = query.filter_by(is_active=True)

    items = query.all()
    return success_response(
        {"items": [i.to_dict() for i in items], "total": len(items)},
        "Daftar titik evakuasi"
    )


@panduan_bp.route("/evakuasi", methods=["POST"])
@jwt_required()
@require_role("admin")
def tambah_evakuasi():
    """POST /api/panduan/evakuasi — tambah titik evakuasi baru."""
    from app.models.evacuation import EvacuationPoint

    user_id = get_jwt_identity()
    data    = request.get_json(silent=True) or {}

    # Validasi wajib
    name      = (data.get("name") or "").strip()
    address   = (data.get("address") or "").strip()
    latitude  = data.get("latitude")
    longitude = data.get("longitude")

    if not name:
        return error_response("name wajib diisi", status_code=400)
    if not address:
        return error_response("address wajib diisi", status_code=400)
    if latitude is None or longitude is None:
        return error_response("latitude dan longitude wajib diisi", status_code=400)

    try:
        latitude  = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return error_response("latitude dan longitude harus berupa angka desimal", status_code=400)

    point = EvacuationPoint(
        name        = name,
        address     = address,
        latitude    = latitude,
        longitude   = longitude,
        capacity    = int(data.get("capacity") or 0),
        description = (data.get("description") or "").strip() or None,
        is_active   = bool(data.get("is_active", True)),
        created_by  = int(user_id),
    )
    db.session.add(point)
    db.session.commit()

    return success_response(point.to_dict(), "Titik evakuasi berhasil ditambahkan"), 201


@panduan_bp.route("/evakuasi/<int:point_id>", methods=["PUT"])
@jwt_required()
@require_role("admin")
def update_evakuasi(point_id):
    """PUT /api/panduan/evakuasi/<id> — update titik evakuasi."""
    from app.models.evacuation import EvacuationPoint

    point = EvacuationPoint.query.get_or_404(point_id)
    data  = request.get_json(silent=True) or {}

    if "name" in data:
        point.name = (data["name"] or "").strip() or point.name
    if "address" in data:
        point.address = (data["address"] or "").strip() or point.address
    if "latitude" in data:
        try:
            point.latitude = float(data["latitude"])
        except (TypeError, ValueError):
            return error_response("latitude harus berupa angka", status_code=400)
    if "longitude" in data:
        try:
            point.longitude = float(data["longitude"])
        except (TypeError, ValueError):
            return error_response("longitude harus berupa angka", status_code=400)
    if "capacity" in data:
        point.capacity = int(data.get("capacity") or 0)
    if "description" in data:
        point.description = (data["description"] or "").strip() or None
    if "is_active" in data:
        point.is_active = bool(data["is_active"])

    db.session.commit()
    return success_response(point.to_dict(), "Titik evakuasi berhasil diperbarui")


@panduan_bp.route("/evakuasi/<int:point_id>", methods=["DELETE"])
@jwt_required()
@require_role("admin")
def hapus_evakuasi(point_id):
    """DELETE /api/panduan/evakuasi/<id> — hapus titik evakuasi."""
    from app.models.evacuation import EvacuationPoint

    point = EvacuationPoint.query.get_or_404(point_id)
    nama  = point.name
    db.session.delete(point)
    db.session.commit()
    return success_response(None, f"Titik evakuasi '{nama}' berhasil dihapus")


# ══════════════════════════════════════════════════════════════════════════════
# KONTAK DARURAT (CRUD — admin only untuk CUD)
# ══════════════════════════════════════════════════════════════════════════════

@panduan_bp.route("/kontak", methods=["GET"])
@jwt_required()
def list_kontak():
    """GET /api/panduan/kontak — daftar semua kontak darurat."""
    from app.models.evacuation import EmergencyContact

    hanya_aktif = request.args.get("aktif", "0") == "1"
    query = EmergencyContact.query.order_by(
        EmergencyContact.sort_order.asc(),
        EmergencyContact.id.asc()
    )
    if hanya_aktif:
        query = query.filter_by(is_active=True)

    items = query.all()
    return success_response(
        {"items": [i.to_dict() for i in items], "total": len(items)},
        "Daftar kontak darurat"
    )


@panduan_bp.route("/kontak", methods=["POST"])
@jwt_required()
@require_role("admin")
def tambah_kontak():
    """POST /api/panduan/kontak — tambah kontak darurat baru."""
    from app.models.evacuation import EmergencyContact

    user_id = get_jwt_identity()
    data    = request.get_json(silent=True) or {}

    name         = (data.get("name") or "").strip()
    phone_number = (data.get("phone_number") or "").strip()
    category     = (data.get("category") or "LAINNYA").upper()

    if not name:
        return error_response("name wajib diisi", status_code=400)
    if not phone_number:
        return error_response("phone_number wajib diisi", status_code=400)
    if category not in EmergencyContact.VALID_CATEGORIES:
        return error_response(
            f"category harus salah satu dari: {', '.join(EmergencyContact.VALID_CATEGORIES)}",
            status_code=400
        )

    kontak = EmergencyContact(
        name         = name,
        category     = category,
        phone_number = phone_number,
        address      = (data.get("address") or "").strip() or None,
        description  = (data.get("description") or "").strip() or None,
        is_active    = bool(data.get("is_active", True)),
        sort_order   = int(data.get("sort_order") or 0),
        created_by   = int(user_id),
    )
    db.session.add(kontak)
    db.session.commit()

    return success_response(kontak.to_dict(), "Kontak darurat berhasil ditambahkan"), 201


@panduan_bp.route("/kontak/<int:kontak_id>", methods=["PUT"])
@jwt_required()
@require_role("admin")
def update_kontak(kontak_id):
    """PUT /api/panduan/kontak/<id> — update kontak darurat."""
    from app.models.evacuation import EmergencyContact

    kontak = EmergencyContact.query.get_or_404(kontak_id)
    data   = request.get_json(silent=True) or {}

    if "name" in data:
        kontak.name = (data["name"] or "").strip() or kontak.name
    if "phone_number" in data:
        kontak.phone_number = (data["phone_number"] or "").strip() or kontak.phone_number
    if "category" in data:
        cat = (data["category"] or "").upper()
        if cat not in EmergencyContact.VALID_CATEGORIES:
            return error_response(
                f"category harus salah satu dari: {', '.join(EmergencyContact.VALID_CATEGORIES)}",
                status_code=400
            )
        kontak.category = cat
    if "address" in data:
        kontak.address = (data["address"] or "").strip() or None
    if "description" in data:
        kontak.description = (data["description"] or "").strip() or None
    if "is_active" in data:
        kontak.is_active = bool(data["is_active"])
    if "sort_order" in data:
        kontak.sort_order = int(data.get("sort_order") or 0)

    db.session.commit()
    return success_response(kontak.to_dict(), "Kontak darurat berhasil diperbarui")


@panduan_bp.route("/kontak/<int:kontak_id>", methods=["DELETE"])
@jwt_required()
@require_role("admin")
def hapus_kontak(kontak_id):
    """DELETE /api/panduan/kontak/<id> — hapus kontak darurat."""
    from app.models.evacuation import EmergencyContact

    kontak = EmergencyContact.query.get_or_404(kontak_id)
    nama   = kontak.name
    db.session.delete(kontak)
    db.session.commit()
    return success_response(None, f"Kontak darurat '{nama}' berhasil dihapus")
