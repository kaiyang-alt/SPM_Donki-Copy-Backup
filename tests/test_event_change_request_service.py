from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app1.services.event_change_request_service import (
    EventChangeRequestNotFoundError,
    EventChangeRequestValidationError,
    create_event_change_request,
    list_change_request_events,
)


@patch(
    "app.services.event_change_request_service.create_authenticated_supabase_client"
)
def test_change_request_event_listing_uses_authenticated_rls_client(
    mock_create_client,
):
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value = (
        SimpleNamespace(data=[{"event_id": "EVT-201", "name": "Authorised Event"}])
    )
    mock_create_client.return_value = client

    events = list_change_request_events("user-access-token")

    assert events == [{"event_id": "EVT-201", "name": "Authorised Event"}]
    mock_create_client.assert_called_once_with("user-access-token")
    client.auth.get_user.assert_called_once_with("user-access-token")
    client.table.assert_called_once_with("event")


def test_create_change_request_requires_change_details():
    with pytest.raises(EventChangeRequestValidationError):
        create_event_change_request(
            "user-access-token", {"event_id": "EVT-201", "change_details": ""}
        )


@patch(
    "app.services.event_change_request_service.create_authenticated_supabase_client"
)
def test_create_change_request_stops_when_rls_does_not_return_event(
    mock_create_client,
):
    client = MagicMock()
    table = client.table.return_value
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[])
    )
    mock_create_client.return_value = client

    with pytest.raises(EventChangeRequestNotFoundError):
        create_event_change_request(
            "user-access-token",
            {
                "event_id": "EVT-301",
                "change_details": "Request changes to an unrelated event.",
            },
        )

    table.insert.assert_not_called()


@patch(
    "app.services.event_change_request_service.create_authenticated_supabase_client"
)
def test_create_change_request_inserts_pending_request(mock_create_client):
    client = MagicMock()
    event_table = MagicMock()
    change_request_table = MagicMock()

    event_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"event_id": "EVT-201", "name": "Authorised Event"}])
    )
    change_request_table.insert.return_value.execute.return_value = SimpleNamespace(
        data=[
            {
                "change_request_id": "CR-001",
                "event_id": "EVT-201",
                "status": "pending",
            }
        ]
    )
    client.table.side_effect = lambda table_name: {
        "event": event_table,
        "event_change_request": change_request_table,
    }[table_name]
    client.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-123")
    )
    mock_create_client.return_value = client

    change_request = create_event_change_request(
        "user-access-token",
        {
            "event_id": "EVT-201",
            "date": "2026-11-20",
            "time": "10:00 AM to 4:00 PM",
            "expected_attendance": 180,
            "programme_timings": "Opening keynote 10:00 AM",
            "venue_requirements": "Lecture theatre with fixed seating",
            "equipment_requirements": "2 wireless microphones",
            "technical_support_requirements": "On-site setup support",
            "change_details": "Increase attendance due to additional speakers.",
        },
    )

    insert_payload = change_request_table.insert.call_args.args[0]

    assert change_request["status"] == "pending"
    assert insert_payload["event_id"] == "EVT-201"
    assert insert_payload["requested_by"] == "user-123"
    assert insert_payload["status"] == "pending"
    assert insert_payload["proposed_changes"]["expected_attendance"] == 180
    assert insert_payload["reason"] == "Increase attendance due to additional speakers."
    assert "change_details" not in insert_payload
