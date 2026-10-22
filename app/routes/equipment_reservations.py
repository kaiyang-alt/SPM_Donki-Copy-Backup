"""Authenticated equipment review endpoints."""

from flask import Blueprint, jsonify, request

from app.services import equipment_reservation_service as service
from app.supabase_client import create_authenticated_supabase_client

equipment_reservations_bp = Blueprint("equipment_reservations", __name__, url_prefix="/api/equipment-requests")


def _handle(action):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer ") or not header[7:].strip():
        return jsonify({"error": "Authentication required."}), 401
    token = header[7:].strip()
    try:
        client = create_authenticated_supabase_client(token)
        user = client.auth.get_user(token).user
        if not user or not user.id:
            raise ValueError("Missing authenticated user")
    except Exception:
        return jsonify({"error": "Authentication required."}), 401
    try:
        return jsonify(action(client, user.id)), 200
    except service.EquipmentError as exc:
        return jsonify({"error": str(exc)}), exc.status_code
    except Exception:
        return jsonify({"error": "Unable to complete the equipment operation. Please try again."}), 503


@equipment_reservations_bp.get("")
def list_requests():
    return _handle(lambda c, u: {"requests": service.list_requests(c, u)})


@equipment_reservations_bp.get("/context")
def context():
    return _handle(service.technical_context)


@equipment_reservations_bp.post("/proposals")
def propose():
    return _handle(lambda c, u: service.propose_quantity(c, u, request.get_json(silent=True)))


@equipment_reservations_bp.get("/organiser")
def organiser_proposals():
    return _handle(lambda c, u: {"requests": service.organiser_proposals(c, u)})


@equipment_reservations_bp.post("/<reservation_id>/agree")
def agree(reservation_id):
    return _handle(lambda c, u: service.agree_proposal(c, u, reservation_id, request.get_json(silent=True)))


@equipment_reservations_bp.get("/<reservation_id>")
def details(reservation_id):
    return _handle(lambda c, u: service.get_request(c, u, reservation_id))


@equipment_reservations_bp.get("/<reservation_id>/availability")
def availability(reservation_id):
    return _handle(lambda c, u: service.availability(c, u, reservation_id))


@equipment_reservations_bp.post("/<reservation_id>/accept")
def accept(reservation_id):
    return _handle(lambda c, u: service.accept_request(c, u, reservation_id))
