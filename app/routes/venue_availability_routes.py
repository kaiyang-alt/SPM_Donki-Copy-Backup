from flask import Blueprint, jsonify, request

from app.services.venue_availability_service import (
    VenueAvailabilityAccessError,
    VenueAvailabilityOverlapError,
    VenueAvailabilityValidationError,
    create_venue_block,
    get_venue_availability,
    list_venue_blocks,
)

venue_availability_bp = Blueprint("venue_availability_api", __name__)


def _bearer_token() -> str | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


@venue_availability_bp.get("/availability")
def get_availability():
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    venue_id = request.args.get("venue_id")
    if not venue_id:
        return jsonify({"error": "venue_id is required."}), 400

    try:
        calendar = get_venue_availability(access_token, venue_id)
    except VenueAvailabilityAccessError:
        return jsonify({"error": "Venue Staff access required."}), 403

    return jsonify({"availability": calendar}), 200


@venue_availability_bp.get("/availability/blocks")
def get_blocks():
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    venue_id = request.args.get("venue_id")
    try:
        blocks = list_venue_blocks(access_token, venue_id=venue_id)
    except VenueAvailabilityAccessError:
        return jsonify({"error": "Venue Staff access required."}), 403

    return jsonify({"blocks": blocks}), 200


@venue_availability_bp.post("/availability/blocks")
def create_block():
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    data = request.get_json(silent=True) or {}

    try:
        block = create_venue_block(access_token, data)
    except VenueAvailabilityValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except VenueAvailabilityOverlapError as exc:
        return jsonify({"error": str(exc)}), 409
    except VenueAvailabilityAccessError:
        return jsonify({"error": "Venue Staff access required."}), 403

    return (
        jsonify(
            {
                "message": "Venue block created successfully.",
                "block": block,
            }
        ),
        201,
    )