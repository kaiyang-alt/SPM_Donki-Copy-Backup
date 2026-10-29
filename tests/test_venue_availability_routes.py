import pytest
from unittest.mock import patch

from app.app import app
from app.services.venue_availability_service import (
    VenueAvailabilityAccessError,
    VenueAvailabilityOverlapError,
    VenueAvailabilityValidationError,
)


@pytest.fixture
def client():
    return app.test_client()


def test_get_availability_requires_authentication(client):
    response = client.get("/api/venue/availability?venue_id=VENUE-1")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication is required."}


def test_get_availability_requires_venue_id(client):
    response = client.get(
        "/api/venue/availability",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "venue_id is required."}


@patch("app.routes.venue_availability_routes.get_venue_availability")
def test_get_availability_returns_unified_calendar(mock_get, client):
    mock_get.return_value = {
        "venue_id": "VENUE-1",
        "confirmed_bookings": [{"id": "REQ-100", "status": "confirmed"}],
        "tentative_holds": [{"id": "REQ-101", "status": "tentative"}],
        "blocks": [{"id": "BLK-1", "date": "2026-12-05"}],
    }

    response = client.get(
        "/api/venue/availability?venue_id=VENUE-1",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    body = response.get_json()["availability"]
    assert body["confirmed_bookings"][0]["id"] == "REQ-100"
    assert body["tentative_holds"][0]["id"] == "REQ-101"
    assert body["blocks"][0]["id"] == "BLK-1"
    mock_get.assert_called_once_with("test-token", "VENUE-1")


@patch("app.routes.venue_availability_routes.get_venue_availability")
def test_get_availability_denies_non_venue_staff(mock_get, client):
    mock_get.side_effect = VenueAvailabilityAccessError(
        "Venue Staff access required."
    )

    response = client.get(
        "/api/venue/availability?venue_id=VENUE-1",
        headers={"Authorization": "Bearer organiser-token"},
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "Venue Staff access required."}


def test_list_blocks_requires_authentication(client):
    response = client.get("/api/venue/availability/blocks?venue_id=VENUE-1")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication is required."}


@patch("app.routes.venue_availability_routes.list_venue_blocks")
def test_list_blocks_returns_rows(mock_list, client):
    mock_list.return_value = [
        {"id": "BLK-1", "venue_id": "VENUE-1", "date": "2026-12-01"}
    ]

    response = client.get(
        "/api/venue/availability/blocks?venue_id=VENUE-1",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "blocks": [{"id": "BLK-1", "venue_id": "VENUE-1", "date": "2026-12-01"}]
    }
    mock_list.assert_called_once_with("test-token", venue_id="VENUE-1")


def test_create_block_requires_authentication(client):
    response = client.post(
        "/api/venue/availability/blocks",
        json={"venue_id": "VENUE-1"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication is required."}


@patch("app.routes.venue_availability_routes.create_venue_block")
def test_create_block_succeeds(mock_create, client):
    mock_create.return_value = {
        "id": "BLK-1",
        "venue_id": "VENUE-1",
        "date": "2026-12-01",
        "start_time": "09:00",
        "end_time": "12:00",
        "status": "blocked",
    }

    response = client.post(
        "/api/venue/availability/blocks",
        headers={"Authorization": "Bearer test-token"},
        json={
            "venue_id": "VENUE-1",
            "date": "2026-12-01",
            "start_time": "09:00",
            "end_time": "12:00",
            "reason": "Scheduled maintenance",
        },
    )

    assert response.status_code == 201
    assert response.get_json()["block"]["id"] == "BLK-1"


@patch("app.routes.venue_availability_routes.create_venue_block")
def test_create_block_rejects_overlap(mock_create, client):
    mock_create.side_effect = VenueAvailabilityOverlapError(
        "Block overlaps a confirmed booking (REQ-100)."
    )

    response = client.post(
        "/api/venue/availability/blocks",
        headers={"Authorization": "Bearer test-token"},
        json={
            "venue_id": "VENUE-1",
            "date": "2026-12-10",
            "start_time": "12:00",
            "end_time": "15:00",
        },
    )

    assert response.status_code == 409
    assert response.get_json() == {
        "error": "Block overlaps a confirmed booking (REQ-100)."
    }


@patch("app.routes.venue_availability_routes.create_venue_block")
def test_create_block_rejects_invalid_input(mock_create, client):
    mock_create.side_effect = VenueAvailabilityValidationError(
        "end_time must be after start_time."
    )

    response = client.post(
        "/api/venue/availability/blocks",
        headers={"Authorization": "Bearer test-token"},
        json={
            "venue_id": "VENUE-1",
            "date": "2026-12-10",
            "start_time": "15:00",
            "end_time": "14:00",
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "end_time must be after start_time."
    }


@patch("app.routes.venue_availability_routes.create_venue_block")
def test_create_block_denies_non_venue_staff(mock_create, client):
    mock_create.side_effect = VenueAvailabilityAccessError(
        "Venue Staff access required."
    )

    response = client.post(
        "/api/venue/availability/blocks",
        headers={"Authorization": "Bearer organiser-token"},
        json={
            "venue_id": "VENUE-1",
            "date": "2026-12-10",
            "start_time": "09:00",
            "end_time": "12:00",
        },
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "Venue Staff access required."}