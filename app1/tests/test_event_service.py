import pytest
from unittest.mock import MagicMock, patch
from app1.services.event_service import get_event_details_for_organiser

# Sample fake data to simulate database responses
MOCK_EVENT_DATA = [{
    "event_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "organiser_id": "11111111-1111-1111-1111-111111111111",
    "name": "Tech Summit 2026",
    "purpose": "Developer Conference",
    "status": "planning",
    "technical_support_required": True,
    "venue_booking": [{"status": "requested", "venue": {"name": "Auditorium"}}],
    "equipment_reservation": []
}]

@patch("app1.services.event_service.supabase")
def test_get_event_details_authorized_success(mock_supabase):
    """Test retrieving event details as the authorized organiser."""
    # Mock Supabase chain: table().select().eq().execute()
    mock_execute = MagicMock()
    mock_execute.data = MOCK_EVENT_DATA
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_execute

    event, error = get_event_details_for_organiser(
        event_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        organiser_id="11111111-1111-1111-1111-111111111111"
    )

    assert error is None
    assert event["name"] == "Tech Summit 2026"
    # Check that outstanding arrangements are correctly calculated
    assert any("Pending Approval" in alert for alert in event["outstanding_arrangements"])


@patch("app1.services.event_service.supabase")
def test_get_event_details_unauthorized_forbidden(mock_supabase):
    """Test that viewing another organiser's event returns UNAUTHORIZED."""
    mock_execute = MagicMock()
    mock_execute.data = MOCK_EVENT_DATA
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_execute

    event, error = get_event_details_for_organiser(
        event_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        organiser_id="99999999-9999-9999-9999-999999999999"  # Unauthorized user ID
    )

    assert event is None
    assert error == "UNAUTHORIZED"