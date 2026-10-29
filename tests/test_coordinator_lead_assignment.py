from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.coordinator_lead_assignment_service import (
    CoordinatorLeadAssignmentError,
    assign_event,
    get_assignment_context,
)


def _client():
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = []
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="lead-1"))
    tables = {
        name: MagicMock()
        for name in ("user_role", "event", "profile", "notification")
    }
    client.table.side_effect = tables.__getitem__
    return client, tables


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_context_lists_only_requested_unassigned_events_and_coordinators(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"role": "event_coordinator_lead"}
    ]
    tables[
        "event"
    ].select.return_value.eq.return_value.is_.return_value.order.return_value.execute.return_value.data = [
        {
            "event_id": "event-1",
            "name": "Regional Innovation Forum 2026",
            "status": "requested",
            "coordinator_id": None,
        }
    ]
    tables[
        "user_role"
    ].select.return_value.eq.return_value.execute.return_value.data = [
        {"user_id": "coordinator-1"}
    ]
    tables["profile"].select.return_value.execute.return_value.data = [
        {"user_id": "coordinator-1", "name": "Maya Tan"},
        {"user_id": "other-1", "name": "Other User"},
    ]

    result = get_assignment_context("token")

    assert result["events"][0]["event_id"] == "event-1"
    assert result["coordinators"] == [
        {"user_id": "coordinator-1", "name": "Maya Tan"}
    ]
    event_query = tables["event"].select.return_value
    event_query.eq.assert_called_once_with("status", "requested")
    event_query.eq.return_value.is_.assert_called_once_with("coordinator_id", "null")


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_lead_assigns_coordinator_without_changing_status_and_notifies_users(
    create_client,
):
    client, tables = _client()
    create_client.return_value = client
    role_execute = (
        tables["user_role"]
        .select.return_value.eq.return_value.eq.return_value.limit.return_value.execute
    )
    role_execute.side_effect = [
        SimpleNamespace(data=[{"role": "event_coordinator_lead"}]),
        SimpleNamespace(data=[{"role": "event_coordinator"}]),
    ]
    event = {
        "event_id": "event-1",
        "name": "Regional Innovation Forum 2026",
        "status": "requested",
        "organiser_id": "organiser-1",
        "coordinator_id": None,
    }
    tables[
        "event"
    ].select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [event]
    client.rpc.return_value.execute.return_value.data = [
        {**event, "coordinator_id": "coordinator-1"}
    ]
    tables[
        "profile"
    ].select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"name": "Maya Tan"}
    ]

    result = assign_event("token", "event-1", "coordinator-1")

    client.rpc.assert_called_once_with(
        "assign_event_coordinator_by_lead",
        {"p_event_id": "event-1", "p_coordinator_id": "coordinator-1"},
    )
    assert result["status"] == "requested"
    assert result["coordinator_name"] == "Maya Tan"
    tables["event"].update.assert_not_called()
    tables["notification"].insert.assert_not_called()


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_non_lead_cannot_load_assignment_context(create_client):
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
def test_already_assigned_event_is_not_reassigned(create_client):
    client, tables = _client()
    create_client.return_value = client
    role_execute = (
        tables["user_role"]
        .select.return_value.eq.return_value.eq.return_value.limit.return_value.execute
    )
    role_execute.side_effect = [
        SimpleNamespace(data=[{"role": "event_coordinator_lead"}]),
        SimpleNamespace(data=[{"role": "event_coordinator"}]),
    ]
    tables[
        "event"
    ].select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {
            "event_id": "event-1",
            "status": "requested",
            "coordinator_id": "coordinator-existing",
        }
    ]

    with pytest.raises(CoordinatorLeadAssignmentError) as error:
        assign_event("token", "event-1", "coordinator-1")

    assert error.value.status == 409
    tables["event"].update.assert_not_called()
    tables["notification"].insert.assert_not_called()
    client.rpc.assert_not_called()


def test_routes_require_authentication_and_object_payload():
    client = app.test_client()
    assert client.get("/api/coordinator-lead/assignment-context").status_code == 401
    assert (
        client.post(
            "/api/coordinator-lead/events/event-1/assign",
            headers={"Authorization": "Bearer token"},
            json=[],
        ).status_code
        == 400
    )


@patch("app.routes.coordinator_lead_assignment.assign_event")
def test_assignment_route_returns_assigned_event(assign):
    assign.return_value = {
        "event_id": "event-1",
        "coordinator_id": "coordinator-1",
        "status": "requested",
    }

    response = app.test_client().post(
        "/api/coordinator-lead/events/event-1/assign",
        headers={"Authorization": "Bearer token"},
        json={"coordinator_id": "coordinator-1"},
    )

    assert response.status_code == 200
    assert response.get_json()["event"]["status"] == "requested"
    assign.assert_called_once_with("token", "event-1", "coordinator-1")
