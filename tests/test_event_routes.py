from unittest.mock import patch

import pytest

from app1.app import app
from app1.services.event_service import EventNotEditableError, EventNotFoundError


@pytest.fixture
def client():
    return app.test_client()


def test_event_list_requires_authentication(client):
    response = client.get("/api/events")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication is required."}


@patch("app1.routes.events.list_authorised_events")
def test_authenticated_organiser_receives_only_service_authorised_events(
    mock_list_events, client
):
    mock_list_events.return_value = [
        {"event_id": "event-1", "name": "Authorised Event"}
    ]

    response = client.get(
        "/api/events", headers={"Authorization": "Bearer access-token"}
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "events": [{"event_id": "event-1", "name": "Authorised Event"}]
    }
    mock_list_events.assert_called_once_with("access-token")


@patch("app1.routes.events.update_authorised_event_name")
def test_authenticated_organiser_can_update_authorised_event(mock_update, client):
    mock_update.return_value = {"event_id": "event-1", "name": "Updated Event"}

    response = client.patch(
        "/api/events/event-1",
        headers={"Authorization": "Bearer access-token"},
        json={"name": "Updated Event"},
    )

    assert response.status_code == 200
    assert response.get_json()["event"]["name"] == "Updated Event"
    mock_update.assert_called_once_with("access-token", "event-1", "Updated Event")


@patch("app1.routes.events.update_authorised_event_name")
def test_unrelated_event_cannot_be_updated(mock_update, client):
    mock_update.side_effect = EventNotFoundError("Event not found.")

    response = client.patch(
        "/api/events/unrelated-event",
        headers={"Authorization": "Bearer access-token"},
        json={"name": "Unauthorised Change"},
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Event not found."}


@patch("app1.routes.events.update_authorised_event_name")
def test_non_editable_event_cannot_be_updated(mock_update, client):
    mock_update.side_effect = EventNotEditableError(
        "The event cannot be edited in its current status."
    )

    response = client.patch(
        "/api/events/confirmed-event",
        headers={"Authorization": "Bearer access-token"},
        json={"name": "Disallowed Change"},
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "The event cannot be edited in its current status."
    }