"""Flask routes for the "Track Event Readiness and Outstanding Actions" user story."""

from flask import Blueprint, jsonify, request

from app.services import track_readiness_actions_service as service
from app.supabase_client import create_authenticated_supabase_client

track_readiness_actions_bp = Blueprint(
    "track_readiness_actions", __name__, url_prefix="/api/track-readiness-actions"
)


def _authenticate():
    """Return (authenticated client, user id) from the caller's Supabase access token."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise service.ReadinessError("Authentication required.", 401)
    token = header[len("Bearer "):].strip()

    try:
        client = create_authenticated_supabase_client(token)
        user_id = client.auth.get_user(token).user.id
    except Exception:
        raise service.ReadinessError("Authentication required.", 401)
    return client, user_id


def _handle(action):
    try:
        client, user_id = _authenticate()
        return action(client, user_id)
    except service.ReadinessError as err:
        return jsonify(err.to_dict()), err.status_code
    except Exception:
        return jsonify({"error": "Something went wrong. Please try again."}), 500


@track_readiness_actions_bp.get("/events")
def list_assigned_events():
    return _handle(lambda c, u: (jsonify({"events": service.list_assigned_events(c, u)}), 200))


@track_readiness_actions_bp.get("/events/<event_id>")
def get_readiness(event_id):
    return _handle(lambda c, u: (jsonify(service.get_readiness(c, u, event_id)), 200))


@track_readiness_actions_bp.post("/events/<event_id>/confirm")
def confirm_event(event_id):
    return _handle(
        lambda c, u: (
            jsonify({"message": "The event has been confirmed.", "event": service.confirm_event(c, u, event_id)}),
            200,
        )
    )