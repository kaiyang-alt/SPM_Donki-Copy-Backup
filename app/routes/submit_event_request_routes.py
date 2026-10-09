"""Flask routes for the "Submit Event Request" user story."""

from flask import Blueprint, jsonify, request

from app.services import submit_event_request_service as service
from app.supabase_client import create_authenticated_supabase_client

event_request_bp = Blueprint("event_requests", __name__, url_prefix="/api/event-requests")


def _authenticate():
    """Return (authenticated client, user id) from the caller's Supabase access token.

    Expects `Authorization: Bearer <access_token>`, the token issued at login.
    """
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise service.EventRequestError("Authentication required.", 401)
    token = header[len("Bearer "):].strip()

    try:
        client = create_authenticated_supabase_client(token)
        user_id = client.auth.get_user(token).user.id
    except Exception:
        raise service.EventRequestError("Authentication required.", 401)
    return client, user_id


def _handle(action):
    try:
        client, user_id = _authenticate()
        return action(client, user_id)
    except service.EventRequestError as err:
        return jsonify(err.to_dict()), err.status_code
    except Exception:
        return jsonify({"error": "Something went wrong. Please try again."}), 500


@event_request_bp.get("")
def list_event_requests():
    return _handle(lambda c, u: (jsonify({"events": service.list_requests(c, u)}), 200))


@event_request_bp.get("/<event_id>")
def get_event_request(event_id):
    return _handle(lambda c, u: (jsonify({"event": service.get_request(c, u, event_id)}), 200))


@event_request_bp.post("/draft")
def save_draft():
    payload = request.get_json(silent=True) or {}
    return _handle(
        lambda c, u: (
            jsonify({"message": "Draft saved.", "event": service.save_draft(c, u, payload)}),
            200,
        )
    )


@event_request_bp.post("/submit")
def submit_event_request():
    payload = request.get_json(silent=True) or {}
    return _handle(
        lambda c, u: (
            jsonify(
                {
                    "message": "Your event request was submitted successfully.",
                    "event": service.submit_request(c, u, payload),
                }
            ),
            201,
        )
    )