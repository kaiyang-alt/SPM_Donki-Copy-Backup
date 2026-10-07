from flask import Blueprint, jsonify, request

from app.services.venue_service import (
    BookingRequestNotFoundError,
    InvalidStatusError,
    VenueAccessError,
    list_venue_booking_requests,
    update_venue_booking_request_status,
)

# No url_prefix — app.py registers this as /api/venue
venue_staff_bp = Blueprint("venue_staff_api", __name__)


def _bearer_token() -> str | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


@venue_staff_bp.get("/requests")
def get_venue_booking_requests():
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    venue_id = request.args.get("venue_id")
    try:
        requests = list_venue_booking_requests(access_token, venue_id=venue_id)
    except VenueAccessError:
        return jsonify({"error": "Venue Staff access required."}), 403

    return jsonify({"requests": requests}), 200


@venue_staff_bp.patch("/requests/<request_id>/status")
def update_request_status(request_id):
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    try:
        updated, warning = update_venue_booking_request_status(
            access_token, request_id, new_status
        )
    except InvalidStatusError as exc:
        return jsonify({"error": str(exc)}), 400
    except BookingRequestNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except VenueAccessError:
        return jsonify({"error": "Venue Staff access required."}), 403

    payload = {
        "message": f"Request status successfully updated to {new_status}",
        "updated_request": updated,
    }
    if warning:
        payload["warning"] = warning
    return jsonify(payload), 200