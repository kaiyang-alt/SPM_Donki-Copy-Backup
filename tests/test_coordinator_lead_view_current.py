from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.coordinator_lead_assignment_service import (
    ACTIVE_EVENT_STATUSES,
    CoordinatorLeadAssignmentError,
    get_current_assignments,
)


def _client():
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="lead-1"))
    tables = {
        name: MagicMock() for name in ("user_role", "event", "profile")
    }
    client.table.side_effect = tables.__getitem__
    return client, tables


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_current_assignments_lists_active_assigned_and_unassigned_events(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"role": "event_coordinator_lead"}
    ]
    tables[
        "event"
    ].select.return_value.in_.return_value.order.return_value.execute.return_value.data = [
        {
            "event_id": "event-1",
            "name": "Community Leadership Summit",
            "status": "planning",
            "coordinator_id": "coordinator-1",
        },
        {
            "event_id": "event-2",
            "name": "Regional Innovation Forum",
            "status": "requested",
            "coordinator_id": None,
        },
    ]
    tables[
        "user_role"
    ].select.return_value.eq.return_value.execute.return_value.data = [
        {"user_id": "coordinator-1"}
    ]
    tables["profile"].select.return_value.execute.return_value.data = [
        {"user_id": "coordinator-1", "name": "Maya Tan"}
    ]

    result = get_current_assignments("token")

    assert result["active_statuses"] == list(ACTIVE_EVENT_STATUSES)
    assert result["events"][0]["assigned"] is True
    assert result["events"][0]["coordinator_name"] == "Maya Tan"
    assert result["events"][1]["assigned"] is False
    assert result["events"][1]["coordinator_name"] is None
    tables["event"].select.return_value.in_.assert_called_once_with(
        "status", list(ACTIVE_EVENT_STATUSES)
    )


@patch(
    "app.services.coordinator_lead_assignment_service.create_authenticated_supabase_client"
)
def test_non_lead_cannot_view_current_assignments(create_client):
    client, tables = _client()
    create_client.return_value = client
    tables[
        "user_role"
    ].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    with pytest.raises(CoordinatorLeadAssignmentError) as error:
        get_current_assignments("token")

    assert error.value.status == 403
    tables["event"].select.assert_not_called()


@patch("app.routes.coordinator_lead_assignment.get_current_assignments")
def test_current_assignments_route_returns_context(get_current):
    get_current.return_value = {
        "events": [
            {
                "event_id": "event-1",
                "coordinator_name": "Maya Tan",
                "assigned": True,
            }
        ],
        "active_statuses": list(ACTIVE_EVENT_STATUSES),
    }
    client = app.test_client()

    response = client.get(
        "/api/coordinator-lead/current-assignments",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert response.get_json()["events"][0]["coordinator_name"] == "Maya Tan"
    get_current.assert_called_once_with("token")


def test_current_assignments_route_requires_authentication():
    client = app.test_client()

    response = client.get("/api/coordinator-lead/current-assignments")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication is required."
