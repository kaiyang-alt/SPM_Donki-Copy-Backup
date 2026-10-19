from flask import Blueprint, jsonify, request

from app.services.event_service import (
    EventAccessError,
    EventNotEditableError,
    EventNotFoundError,
    list_authorised_events,
    update_authorised_event_name,
)


events_blueprint = Blueprint("events", __name__, url_prefix="/api/events")


def _bearer_token() -> str | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


@events_blueprint.get("")
def get_events():
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    try:
        events = list_authorised_events(access_token)
    except EventAccessError:
        return jsonify({"error": "The authenticated session is invalid."}), 401

    return jsonify({"events": events}), 200


@events_blueprint.patch("/<event_id>")
def update_event(event_id: str):
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    data = request.get_json(silent=True) or {}
    event_name = str(data.get("name", "")).strip()
    if not event_name:
        return jsonify({"error": "Event name is required."}), 400

    try:
        event = update_authorised_event_name(access_token, event_id, event_name)
    except EventNotFoundError:
        return jsonify({"error": "Event not found."}), 404
    except EventNotEditableError as exc:
        return jsonify({"error": str(exc)}), 409
    except EventAccessError:
        return jsonify({"error": "The event could not be updated."}), 403

    return jsonify({"event": event}), 200
