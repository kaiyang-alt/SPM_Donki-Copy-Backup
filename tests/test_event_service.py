from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.event_service import (
    EventNotEditableError,
    EventNotFoundError,
    list_authorised_events,
    update_authorised_event_name,
)


@patch("app.services.event_service.create_authenticated_supabase_client")
def test_event_listing_uses_authenticated_rls_client(mock_create_client):
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value = SimpleNamespace(
        data=[{"event_id": "event-1", "name": "Authorised Event"}]
    )
    mock_create_client.return_value = client

    events = list_authorised_events("user-access-token")

    assert events == [{"event_id": "event-1", "name": "Authorised Event"}]
    mock_create_client.assert_called_once_with("user-access-token")
    client.auth.get_user.assert_called_once_with("user-access-token")
    client.table.assert_called_once_with("event")


@patch("app.services.event_service.create_authenticated_supabase_client")
def test_update_stops_when_rls_does_not_return_event(mock_create_client):
    client = MagicMock()
    query = client.table.return_value.select.return_value.eq.return_value
    query.limit.return_value.execute.return_value = SimpleNamespace(data=[])
    mock_create_client.return_value = client

    with pytest.raises(EventNotFoundError):
        update_authorised_event_name(
            "user-access-token", "unrelated-event", "Unauthorised Change"
        )

    client.table.return_value.update.assert_not_called()


@pytest.mark.parametrize("editable_status", ["draft", "requested", "changes_requested"])
@patch("app.services.event_service.create_authenticated_supabase_client")
def test_event_name_can_be_updated_in_organiser_editable_status(
    mock_create_client, editable_status
):
    client = MagicMock()
    table = client.table.return_value
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(
            data=[
                {
                    "event_id": "event-1",
                    "name": "Original",
                    "status": editable_status,
                }
            ]
        )
    )
    table.update.return_value.eq.return_value.execute.return_value = SimpleNamespace(
        data=[
            {"event_id": "event-1", "name": "Updated", "status": editable_status}
        ]
    )
    mock_create_client.return_value = client

    event = update_authorised_event_name("user-access-token", "event-1", "Updated")

    assert event["name"] == "Updated"
    table.update.assert_called_once_with({"name": "Updated"})
    table.update.return_value.eq.assert_called_once_with("event_id", "event-1")


@patch("app.services.event_service.create_authenticated_supabase_client")
def test_non_editable_event_name_cannot_be_updated(mock_create_client):
    client = MagicMock()
    table = client.table.return_value
    table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(
            data=[
                {"event_id": "event-1", "name": "Confirmed", "status": "confirmed"}
            ]
        )
    )
    mock_create_client.return_value = client

    with pytest.raises(EventNotEditableError):
        update_authorised_event_name("user-access-token", "event-1", "Disallowed")

    table.update.assert_not_called()
