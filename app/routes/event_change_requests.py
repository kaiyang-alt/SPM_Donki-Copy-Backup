from flask import Blueprint, current_app, jsonify, request

from app.services.event_change_request_service import (
    EventChangeRequestAccessError,
    EventChangeRequestNotFoundError,
    EventChangeRequestValidationError,
    create_event_change_request,
    list_change_request_events,
)


event_change_requests_blueprint = Blueprint(
    "event_change_requests", __name__, url_prefix="/api/event-change-requests"
)


def _bearer_token() -> str | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


@event_change_requests_blueprint.get("/events")
def get_change_request_events():
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    try:
        events = list_change_request_events(access_token)
    except EventChangeRequestAccessError:
        return jsonify({"error": "The authenticated session is invalid."}), 401

    return jsonify({"events": events}), 200


@event_change_requests_blueprint.post("")
def submit_change_request():
    access_token = _bearer_token()
    if not access_token:
        return jsonify({"error": "Authentication is required."}), 401

    data = request.get_json(silent=True) or {}

    try:
        change_request = create_event_change_request(access_token, data)
    except EventChangeRequestValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except EventChangeRequestNotFoundError:
        return jsonify({"error": "Event not found."}), 404
    except EventChangeRequestAccessError as exc:
        current_app.logger.exception(
            "Event change request submission failed: %s",
            getattr(exc, "original_error", exc),
        )
        return jsonify({"error": "The change request could not be submitted."}), 403

    return (
        jsonify(
            {
                "message": "Change request submitted successfully.",
                "change_request": change_request,
            }
        ),
        201,
    )
