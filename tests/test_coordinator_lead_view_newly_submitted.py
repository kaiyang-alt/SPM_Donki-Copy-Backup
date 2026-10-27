from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.coordinator_lead_assignment_service import (
    CoordinatorLeadAssignmentError,
    get_assignment_context,
    get_unassigned_event_request,
)


def _client():
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="lead-1"))
    tables = {name: MagicMock() for name in ("user_role", "event", "profile")}
    client.table.side_effect = tables.__getitem__
    return client, tables


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_queue_returns_requested_unassigned_event_with_basic_information(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"role": "event_coordinator_lead"}
    ]
    event = {
        "event_id": "event-301",
        "name": "Regional Innovation Forum 2026",
        "status": "requested",
        "preferred_start_datetime": "2026-11-25T09:00:00+08:00",
        "preferred_end_datetime": "2026-11-25T17:00:00+08:00",
        "expected_attendance": 180,
        "coordinator_id": None,
    }
    tables[
        "event"
    ].select.return_value.eq.return_value.is_.return_value.order.return_value.execute.return_value.data = [
        event
    ]
    tables[
        "user_role"
    ].select.return_value.eq.return_value.execute.return_value.data = []
    tables["profile"].select.return_value.execute.return_value.data = []

    result = get_assignment_context("token")

    assert result["events"] == [event]
    selected_columns = tables["event"].select.call_args.args[0]
    for field in (
        "event_id",
        "name",
        "status",
        "preferred_start_datetime",
        "preferred_end_datetime",
        "expected_attendance",
        "coordinator_id",
    ):
        assert field in selected_columns
    tables["event"].select.return_value.eq.assert_called_once_with(
        "status", "requested"
    )
    tables["event"].select.return_value.eq.return_value.is_.assert_called_once_with(
        "coordinator_id", "null"
    )


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_non_lead_cannot_view_newly_submitted_queue(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with pytest.raises(CoordinatorLeadAssignmentError) as error:
        get_assignment_context("token")

    assert error.value.status == 403
    tables["event"].select.assert_not_called()


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_lead_opens_unassigned_request_with_available_event_information(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"role": "event_coordinator_lead"}
    ]
    event = {
        "event_id": "event-301",
        "name": "Regional Innovation Forum 2026",
        "purpose": "Regional collaboration",
        "description": "A forum for regional innovators.",
        "status": "requested",
        "venue_requirements": "Accessible lecture theatre",
        "technical_requirements": "Projector and microphones",
        "coordinator_id": None,
    }
    query = tables["event"].select.return_value
    query.eq.return_value = query
    query.is_.return_value = query
    query.limit.return_value = query
    query.execute.return_value.data = [event]

    result = get_unassigned_event_request("token", "event-301")

    assert result == event
    query.eq.assert_any_call("event_id", "event-301")
    query.eq.assert_any_call("status", "requested")
    query.is_.assert_called_once_with("coordinator_id", "null")


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_assigned_or_non_requested_event_cannot_be_opened_from_unassigned_queue(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"role": "event_coordinator_lead"}
    ]
    query = tables["event"].select.return_value
    query.eq.return_value = query
    query.is_.return_value = query
    query.limit.return_value = query
    query.execute.return_value.data = []

    with pytest.raises(CoordinatorLeadAssignmentError) as error:
        get_unassigned_event_request("token", "event-302")

    assert error.value.status == 404


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_non_lead_cannot_open_unassigned_request(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with pytest.raises(CoordinatorLeadAssignmentError) as error:
        get_unassigned_event_request("token", "event-301")

    assert error.value.status == 403
    tables["event"].select.assert_not_called()


def test_unassigned_queue_route_requires_authentication():
    response = app.test_client().get("/api/coordinator-lead/assignment-context")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication is required."


@patch("app.routes.coordinator_lead_assignment.get_unassigned_event_request")
def test_unassigned_request_route_returns_event_details(get_request):
    get_request.return_value = {
        "event_id": "event-301",
        "name": "Regional Innovation Forum 2026",
        "status": "requested",
        "coordinator_id": None,
    }

    response = app.test_client().get(
        "/api/coordinator-lead/events/event-301/unassigned-request",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert response.get_json()["event"]["event_id"] == "event-301"
    get_request.assert_called_once_with("token", "event-301")
