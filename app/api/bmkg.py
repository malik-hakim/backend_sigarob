from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.utils.responses import success_response, error_response

bmkg_bp = Blueprint("bmkg", __name__)


# GET /api/bmkg/latest — data BMKG terbaru dari DB
@bmkg_bp.route("/latest", methods=["GET"])
@jwt_required()
def latest():
    from app.services.bmkg_service import get_latest_bmkg
    data = get_latest_bmkg()
    if not data:
        return error_response("Belum ada data BMKG", "NOT_FOUND", 404)
    return success_response(data, "Data BMKG terbaru")


# POST /api/bmkg/fetch — trigger fetch manual dari BMKG API
@bmkg_bp.route("/fetch", methods=["POST"])
@jwt_required()
def fetch_manual():
    from app.services.bmkg_service import fetch_dan_simpan_bmkg
    try:
        data = fetch_dan_simpan_bmkg()
        return success_response(data, "Data BMKG berhasil diperbarui")
    except Exception as e:
        return error_response(str(e), "FETCH_ERROR", 502)


# GET /api/bmkg/history — riwayat fetch BMKG
@bmkg_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    from app.models.bmkg import BmkgForecast
    page     = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)

    pagination = (
        BmkgForecast.query
        .order_by(BmkgForecast.fetched_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return success_response({
        "items":  [r.to_dict() for r in pagination.items],
        "total":  pagination.total,
        "page":   pagination.page,
        "pages":  pagination.pages,
    }, "Riwayat data BMKG")