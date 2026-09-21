from flask import Blueprint, jsonify, request
from app.services.event_service import EventNotFoundError, EventNotEditableError

events_bp = Blueprint("events_api", __name__, url_prefix="/api/events")


def list_authorised_events(token):
    return []


def update_authorised_event_name(token, event_id, new_name):
    return {"event_id": event_id, "name": new_name}


@events_bp.route("", methods=["GET"])
def get_events():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authentication is required."}), 401

    token = auth_header.split(" ")[1]
    events = list_authorised_events(token)
    return jsonify({"events": events}), 200


@events_bp.route("/<event_id>", methods=["PATCH"])
def update_event_name(event_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Authentication is required."}), 401

    token = auth_header.split(" ")[1]
    data = request.get_json() or {}
    new_name = data.get("name")

    try:
        updated_event = update_authorised_event_name(token, event_id, new_name)
        return jsonify({"event": updated_event}), 200
    except EventNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except EventNotEditableError as e:
        return jsonify({"error": str(e)}), 409
