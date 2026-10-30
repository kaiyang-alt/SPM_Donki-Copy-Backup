from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.venue_availability_service import (
    VenueAvailabilityAccessError,
    VenueAvailabilityOverlapError,
    VenueAvailabilityValidationError,
    create_venue_block,
    get_venue_availability,
)


def _staff_client():
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-1")
    )
    role_query = MagicMock()
    role_query.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[{"role": "venue_staff"}])
    )
    return client, role_query


def _non_staff_client():
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-2")
    )
    role_query = MagicMock()
    role_query.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[])
    )
    return client, role_query


@patch(
    "app.services.venue_availability_service.create_authenticated_supabase_client"
)
def test_get_venue_availability_merges_bookings_and_blocks(mock_create):
    client, role_query = _staff_client()

    booking_table = MagicMock()
    block_table = MagicMock()

    booking_table.select.return_value.eq.return_value.execute.return_value = (
        SimpleNamespace(data=[
            {"id": "REQ-100", "status": "confirmed", "start_time": "10:00", "end_time": "14:00"},
            {"id": "REQ-101", "status": "tentative", "start_time": "14:00", "end_time": "16:00"},
            {"id": "REQ-102", "status": "pending", "start_time": "16:00", "end_time": "17:00"},
        ])
    )
    block_table.select.return_value.eq.return_value.execute.return_value = (
        SimpleNamespace(data=[{"id": "BLK-1", "date": "2026-12-05"}])
    )

    client.table.side_effect = lambda name: {
        "user_role": role_query,
        "venue_booking": booking_table,
        "venue_block": block_table,
    }[name]
    mock_create.return_value = client

    result = get_venue_availability("token", "VENUE-1")

    assert result["venue_id"] == "VENUE-1"
    assert len(result["confirmed_bookings"]) == 1
    assert len(result["tentative_holds"]) == 2
    assert len(result["blocks"]) == 1


@patch(
    "app.services.venue_availability_service.create_authenticated_supabase_client"
)
def test_get_venue_availability_denies_non_staff(mock_create):
    client, role_query = _non_staff_client()
    client.table.side_effect = lambda name: {"user_role": role_query}[name]
    mock_create.return_value = client

    with pytest.raises(VenueAvailabilityAccessError):
        get_venue_availability("token", "VENUE-1")


def test_create_block_requires_venue_id():
    with pytest.raises(VenueAvailabilityValidationError):
        create_venue_block(
            "token",
            {
                "date": "2026-12-10",
                "start_time": "09:00",
                "end_time": "12:00",
            },
        )


def test_create_block_requires_date():
    with pytest.raises(VenueAvailabilityValidationError):
        create_venue_block(
            "token",
            {
                "venue_id": "VENUE-1",
                "start_time": "09:00",
                "end_time": "12:00",
            },
        )


def test_create_block_rejects_end_before_start():
    with pytest.raises(VenueAvailabilityValidationError):
        create_venue_block(
            "token",
            {
                "venue_id": "VENUE-1",
                "date": "2026-12-10",
                "start_time": "15:00",
                "end_time": "14:00",
            },
        )


@patch(
    "app.services.venue_availability_service.create_authenticated_supabase_client"
)
def test_create_block_rejects_overlap_with_confirmed_booking(mock_create):
    client, role_query = _staff_client()

    booking_table = MagicMock()
    booking_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = (
        SimpleNamespace(data=[
            {"id": "REQ-100", "status": "confirmed", "start_time": "10:00", "end_time": "14:00"}
        ])
    )
    block_table = MagicMock()

    client.table.side_effect = lambda name: {
        "user_role": role_query,
        "venue_booking": booking_table,
        "venue_block": block_table,
    }[name]
    mock_create.return_value = client

    with pytest.raises(VenueAvailabilityOverlapError):
        create_venue_block(
            "token",
            {
                "venue_id": "VENUE-1",
                "date": "2026-12-10",
                "start_time": "12:00",
                "end_time": "15:00",
            },
        )

    block_table.insert.assert_not_called()


@patch(
    "app.services.venue_availability_service.create_authenticated_supabase_client"
)
def test_create_block_inserts_when_no_overlap(mock_create):
    client, role_query = _staff_client()

    booking_table = MagicMock()
    booking_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = (
        SimpleNamespace(data=[
            {"id": "REQ-100", "status": "confirmed", "start_time": "10:00", "end_time": "14:00"}
        ])
    )
    block_table = MagicMock()
    block_table.insert.return_value.execute.return_value = SimpleNamespace(
        data=[{
            "id": "BLK-2",
            "venue_id": "VENUE-1",
            "date": "2026-12-10",
            "start_time": "14:00",
            "end_time": "16:00",
            "status": "blocked",
        }]
    )

    client.table.side_effect = lambda name: {
        "user_role": role_query,
        "venue_booking": booking_table,
        "venue_block": block_table,
    }[name]
    mock_create.return_value = client

    result = create_venue_block(
        "token",
        {
            "venue_id": "VENUE-1",
            "date": "2026-12-10",
            "start_time": "14:00",
            "end_time": "16:00",
            "reason": "Maintenance",
        },
    )

    assert result["id"] == "BLK-2"
    insert_payload = block_table.insert.call_args.args[0]
    assert insert_payload["venue_id"] == "VENUE-1"
    assert insert_payload["status"] == "blocked"
    assert insert_payload["reason"] == "Maintenance"


@patch(
    "app.services.venue_availability_service.create_authenticated_supabase_client"
)
def test_create_block_denies_non_staff(mock_create):
    client, role_query = _non_staff_client()
    client.table.side_effect = lambda name: {"user_role": role_query}[name]
    mock_create.return_value = client

    with pytest.raises(VenueAvailabilityAccessError):
        create_venue_block(
            "token",
            {
                "venue_id": "VENUE-1",
                "date": "2026-12-10",
                "start_time": "09:00",
                "end_time": "12:00",
            },
        )