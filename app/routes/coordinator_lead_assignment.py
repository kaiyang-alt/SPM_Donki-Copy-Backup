from flask import Blueprint, jsonify, request

from app.services.coordinator_lead_assignment_service import (
    CoordinatorLeadAssignmentError,
    assign_event,
    get_assigned_event_details,
    get_assignment_context,
    get_current_assignments,
    get_reassignment_context,
    reassign_event,
)


coordinator_lead_assignment_blueprint = Blueprint(
    "coordinator_lead_assignment",
    __name__,
    url_prefix="/api/coordinator-lead",
)


def _token():
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


def _error_response(operation):
    token = _token()
    if not token:
        return jsonify(error="Authentication is required."), 401
    try:
        return jsonify(operation(token)), 200
    except CoordinatorLeadAssignmentError as exc:
        return jsonify(error=str(exc)), exc.status


@coordinator_lead_assignment_blueprint.get("/assignment-context")
def assignment_context():
    return _error_response(get_assignment_context)


@coordinator_lead_assignment_blueprint.get("/reassignment-context")
def reassignment_context():
    return _error_response(get_reassignment_context)


@coordinator_lead_assignment_blueprint.get("/current-assignments")
def current_assignments():
    return _error_response(get_current_assignments)


@coordinator_lead_assignment_blueprint.get("/events/<event_id>/assignment-details")
def assigned_event_details(event_id):
    return _error_response(
        lambda token: {"event": get_assigned_event_details(token, event_id)}
    )


@coordinator_lead_assignment_blueprint.post("/events/<event_id>/assign")
def assign(event_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="A JSON object is required."), 400
    return _error_response(
        lambda token: {
            "event": assign_event(token, event_id, payload.get("coordinator_id"))
        }
    )


@coordinator_lead_assignment_blueprint.post("/events/<event_id>/reassign")
def reassign(event_id):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="A JSON object is required."), 400
    return _error_response(
        lambda token: {
            "event": reassign_event(token, event_id, payload.get("coordinator_id"))
        }
    )
