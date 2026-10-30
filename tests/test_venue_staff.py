import pytest
from unittest.mock import patch

from app.app import app
from app.services.venue_service import InvalidStatusError, VenueAccessError


@pytest.fixture
def client():
    return app.test_client()


@patch("app.routes.venue_staff_routes.list_venue_booking_requests")
def test_get_requests_chronological_order(mock_list_svc, client):
    """TC-002: Competing pending requests are returned in submission order."""
    mock_list_svc.return_value = [
        {"id": "REQ-1", "submitted_at": "2026-10-07T08:00:00Z", "status": "pending"},
        {"id": "REQ-2", "submitted_at": "2026-10-07T09:30:00Z", "status": "pending"},
    ]

    response = client.get(
        "/api/venue/requests",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    data = response.get_json()["requests"]
    assert len(data) == 2
    assert data[0]["id"] == "REQ-1"
    mock_list_svc.assert_called_once_with("test-token", venue_id=None)


def test_unauthenticated_access_is_rejected(client):
    """TC-005a: Missing bearer token → 401."""
    response = client.get("/api/venue/requests")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication is required."}


@patch("app.routes.venue_staff_routes.list_venue_booking_requests")
def test_non_venue_staff_access_is_denied(mock_list_svc, client):
    """TC-005b: Authenticated but not Venue Staff → 403."""
    mock_list_svc.side_effect = VenueAccessError("Venue Staff access required.")

    response = client.get(
        "/api/venue/requests",
        headers={"Authorization": "Bearer organiser-token"},
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "Venue Staff access required."}


@patch("app.routes.venue_staff_routes.update_venue_booking_request_status")
def test_update_status_returns_warning_on_overlap(mock_update, client):
    mock_update.return_value = (
        {"id": "REQ-1", "status": "approved"},
        {
            "message": (
                "Approval creates schedule conflict with "
                "1 remaining pending request(s)."
            ),
            "conflicting_request_ids": ["REQ-2"],
        },
    )

    response = client.patch(
        "/api/venue/requests/REQ-1/status",
        headers={"Authorization": "Bearer test-token"},
        json={"status": "approved"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["updated_request"]["status"] == "approved"
    assert "warning" in body


@patch("app.routes.venue_staff_routes.update_venue_booking_request_status")
def test_update_status_rejects_invalid_value(mock_update, client):
    mock_update.side_effect = InvalidStatusError(
        "Invalid status. Must be 'approved' or 'rejected'."
    )

    response = client.patch(
        "/api/venue/requests/REQ-1/status",
        headers={"Authorization": "Bearer test-token"},
        json={"status": "maybe"},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Invalid status. Must be 'approved' or 'rejected'."
    }