import uuid

from flask import Blueprint, current_app, jsonify, request

from app.services import event_assignment_service as service
from app.supabase_client import create_authenticated_supabase_client


event_assignment_bp = Blueprint(
    "event_assignment", __name__, url_prefix="/api/event-assignment"
)


def _get_bearer_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):].strip() or None
    return None


def _authenticate():
    token = _get_bearer_token()
    if not token:
        raise service.AuthenticationError("Please log in to continue.")
    client = create_authenticated_supabase_client(token)
    user_id = service.get_current_user_id(client, token)
    return client, user_id


def _error(message, status_code):
    return jsonify({"error": message}), status_code


@event_assignment_bp.route("/assigned-events", methods=["GET"])
def list_assigned_events():
    try:
        client, user_id = _authenticate()
        events = service.get_assigned_events(client, user_id)
    except service.EventAssignmentError as exc:
        return _error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Failed to load assigned events")
        return _error("Unable to load assigned events. Please try again.", 500)

    return jsonify({"events": events}), 200


@event_assignment_bp.route("/events/<event_id>", methods=["GET"])
def get_event_assignment(event_id):
    try:
        uuid.UUID(event_id)
    except ValueError:
        return _error("Event not found.", 404)

    try:
        client, user_id = _authenticate()
        assignment = service.get_event_assignment(client, user_id, event_id)
    except service.EventAssignmentError as exc:
        return _error(str(exc), exc.status_code)
    except Exception:
        current_app.logger.exception("Failed to load event assignment")
        return _error("Unable to load the event assignment. Please try again.", 500)

    return jsonify(assignment), 200