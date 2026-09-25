from unittest.mock import patch

import pytest

from app.app import app
from app.services.event_change_request_service import (
    EventChangeRequestAccessError,
    EventChangeRequestNotFoundError,
    EventChangeRequestValidationError,
)


@pytest.fixture
def client():
    return app.test_client()


def test_change_request_event_list_requires_authentication(client):
    response = client.get("/api/event-change-requests/events")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication is required."}


@patch("app.routes.event_change_requests.list_change_request_events")
def test_authenticated_organiser_can_list_authorised_change_request_events(
    mock_list_events, client
):
    mock_list_events.return_value = [
        {"event_id": "EVT-201", "name": "Regional Business Conference 2026"}
    ]

    response = client.get(
        "/api/event-change-requests/events",
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "events": [
            {"event_id": "EVT-201", "name": "Regional Business Conference 2026"}
        ]
    }
    mock_list_events.assert_called_once_with("access-token")


def test_submit_change_request_requires_authentication(client):
    response = client.post("/api/event-change-requests", json={})

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication is required."}


@patch("app.routes.event_change_requests.create_event_change_request")
def test_submit_change_request_requires_change_details(mock_create, client):
    mock_create.side_effect = EventChangeRequestValidationError(
        "Change details are required."
    )

    response = client.post(
        "/api/event-change-requests",
        headers={"Authorization": "Bearer access-token"},
        json={"event_id": "EVT-201", "change_details": ""},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "Change details are required."}


@patch("app.routes.event_change_requests.create_event_change_request")
def test_submit_change_request_rejects_unauthorised_event(mock_create, client):
    mock_create.side_effect = EventChangeRequestNotFoundError("Event not found.")

    response = client.post(
        "/api/event-change-requests",
        headers={"Authorization": "Bearer access-token"},
        json={
            "event_id": "EVT-301",
            "change_details": "Request changes to an unrelated event.",
        },
    )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Event not found."}


@patch("app.routes.event_change_requests.create_event_change_request")
def test_submit_change_request_returns_pending_request(mock_create, client):
    mock_create.return_value = {
        "change_request_id": "CR-001",
        "event_id": "EVT-201",
        "status": "pending",
    }

    response = client.post(
        "/api/event-change-requests",
        headers={"Authorization": "Bearer access-token"},
        json={
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

    assert response.status_code == 201
    assert response.get_json()["change_request"]["status"] == "pending"
    mock_create.assert_called_once()


@patch("app.routes.event_change_requests.create_event_change_request")
def test_submit_change_request_handles_access_error(mock_create, client):
    mock_create.side_effect = EventChangeRequestAccessError(
        "Unable to submit the change request."
    )

    response = client.post(
        "/api/event-change-requests",
        headers={"Authorization": "Bearer access-token"},
        json={
            "event_id": "EVT-201",
            "change_details": "Increase attendance due to additional speakers.",
        },
    )

    assert response.status_code == 403
    assert response.get_json() == {
        "error": "The change request could not be submitted."
    }
