from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.coordinator_lead_assignment_service import (
    CoordinatorLeadAssignmentError,
    get_reassignment_context,
    reassign_event,
)


def _client():
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="lead-1"))
    tables = {
        name: MagicMock()
        for name in ("user_role", "event", "profile", "notification")
    }
    client.table.side_effect = tables.__getitem__
    return client, tables


def _lead_and_coordinator_roles(tables):
    execute = (
        tables["user_role"]
        .select.return_value.eq.return_value.eq.return_value.limit.return_value.execute
    )
    execute.side_effect = [
        SimpleNamespace(data=[{"role": "event_coordinator_lead"}]),
        SimpleNamespace(data=[{"role": "event_coordinator"}]),
    ]


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_reassignment_context_displays_current_coordinator(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"role": "event_coordinator_lead"}
    ]
    tables[
        "event"
    ].select.return_value.not_.is_.return_value.order.return_value.execute.return_value.data = [
        {
            "event_id": "event-1",
            "name": "Digital Futures Forum",
            "coordinator_id": "coordinator-1",
        }
    ]
    tables[
        "user_role"
    ].select.return_value.eq.return_value.execute.return_value.data = [
        {"user_id": "coordinator-1"},
        {"user_id": "coordinator-2"},
    ]
    tables["profile"].select.return_value.execute.return_value.data = [
        {"user_id": "coordinator-1", "name": "Maya Tan"},
        {"user_id": "coordinator-2", "name": "Daniel Koh"},
    ]

    result = get_reassignment_context("token")

    assert result["events"][0]["coordinator_name"] == "Maya Tan"
    assert [row["name"] for row in result["coordinators"]] == [
        "Daniel Koh",
        "Maya Tan",
    ]


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_lead_reassigns_event_and_notifies_outgoing_incoming_and_organiser(
    create_client,
):
    client, tables = _client()
    create_client.return_value = client
    _lead_and_coordinator_roles(tables)
    event = {
        "event_id": "event-1",
        "name": "Digital Futures Forum",
        "status": "planning",
        "organiser_id": "organiser-1",
        "coordinator_id": "coordinator-1",
    }
    tables[
        "event"
    ].select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [event]
    update = tables["event"].update.return_value
    update.eq.return_value = update
    update.execute.return_value.data = [
        {**event, "coordinator_id": "coordinator-2"}
    ]
    tables["notification"].insert.return_value.execute.return_value.data = [
        {"notification_id": "notification-1"},
        {"notification_id": "notification-2"},
        {"notification_id": "notification-3"},
    ]
    tables[
        "profile"
    ].select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"name": "Daniel Koh"}
    ]

    result = reassign_event("token", "event-1", "coordinator-2")

    assert result["coordinator_id"] == "coordinator-2"
    assert result["coordinator_name"] == "Daniel Koh"
    assert result["previous_coordinator_id"] == "coordinator-1"
    update.eq.assert_any_call("event_id", "event-1")
    update.eq.assert_any_call("coordinator_id", "coordinator-1")
    notifications = tables["notification"].insert.call_args.args[0]
    assert {row["recipient_id"] for row in notifications} == {
        "coordinator-1",
        "coordinator-2",
        "organiser-1",
    }
    assert {row["type"] for row in notifications} == {"coordinator_reassigned"}


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_reassignment_rejects_current_coordinator_as_replacement(create_client):
    client, tables = _client()
    create_client.return_value = client
    _lead_and_coordinator_roles(tables)
    tables[
        "event"
    ].select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {
            "event_id": "event-1",
            "coordinator_id": "coordinator-1",
        }
    ]

    with pytest.raises(CoordinatorLeadAssignmentError) as error:
        reassign_event("token", "event-1", "coordinator-1")

    assert "different Event Coordinator" in str(error.value)
    tables["event"].update.assert_not_called()
    tables["notification"].insert.assert_not_called()


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_reassignment_rejects_unassigned_event(create_client):
    client, tables = _client()
    create_client.return_value = client
    _lead_and_coordinator_roles(tables)
    tables[
        "event"
    ].select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"event_id": "event-1", "coordinator_id": None}
    ]

    with pytest.raises(CoordinatorLeadAssignmentError) as error:
        reassign_event("token", "event-1", "coordinator-2")

    assert error.value.status == 409
    tables["event"].update.assert_not_called()


def test_reassignment_route_requires_json_object():
    client = app.test_client()

    response = client.post(
        "/api/coordinator-lead/events/event-1/reassign",
        data="not-json",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "A JSON object is required."


@patch("app.routes.coordinator_lead_assignment.reassign_event")
def test_reassignment_route_returns_updated_assignment(reassign):
    reassign.return_value = {
        "event_id": "event-1",
        "coordinator_id": "coordinator-2",
        "coordinator_name": "Daniel Koh",
    }
    client = app.test_client()

    response = client.post(
        "/api/coordinator-lead/events/event-1/reassign",
        json={"coordinator_id": "coordinator-2"},
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert response.get_json()["event"]["coordinator_name"] == "Daniel Koh"
    reassign.assert_called_once_with("token", "event-1", "coordinator-2")
