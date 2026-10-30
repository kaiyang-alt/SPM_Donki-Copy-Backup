"""Flask acceptance targets for the approved venue-alternatives workflow.

Run: python3 -m pytest tests/test_venue_booking_alternatives.py -v
Mocks verify the Flask/service contract, not SQL atomicity or transfer allocation.
Those guarantees are exercised by test_venue_booking_alternatives.sql.
"""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from test_venue_booking import (
    END,
    HEADERS,
    PAYLOAD,
    START,
    Query,
    active_booking,
    client,
    database,
    submit,
)


@pytest.fixture
def alternatives_db(database):
    """Reuse the canonical fixture with two eligible alternative venues."""
    database.rows["venue"][0].update(setup_minutes=15, turnaround_minutes=15)
    database.rows["venue"].append(
        {
            **deepcopy(database.rows["venue"][0]),
            "venue_id": "VEN-002",
            "name": "Seminar Room",
            "supported_layouts": ["Classroom"],
        }
    )
    database.rpc = MagicMock()
    database.rpc.return_value.execute.return_value = SimpleNamespace(data=True)
    return database


def test_tc_007_submit_two_alternatives_with_independent_periods(client, alternatives_db):
    first = submit(client)
    assert first.status_code == 201
    second = submit(
        client,
        {
            **PAYLOAD,
            "venue_id": "VEN-002",
            "booking_date": "2026-11-16",
            "start_time": "13:00",
            "end_time": "16:00",
            "setup_layout": "Classroom",
        },
    )
    assert second.status_code == 201
    bookings = alternatives_db.rows["venue_booking"]
    assert len(bookings) == 2
    assert {row["event_id"] for row in bookings} == {PAYLOAD["event_id"]}
    assert {row["status"] for row in bookings} == {"requested"}
    assert bookings[0]["requested_start"] == START
    assert bookings[1]["requested_start"] == "2026-11-16T13:00:00+08:00"
    assert bookings[1]["requested_end"] == "2026-11-16T16:00:00+08:00"


@pytest.mark.parametrize("status", ["requested", "tentative"])
def test_tc_007_other_event_pending_alternative_does_not_block(
    client, alternatives_db, status
):
    alternatives_db.rows["venue_booking"].append(active_booking(status=status))
    response = submit(client)
    assert response.status_code == 201
    assert len(alternatives_db.rows["venue_booking"]) == 2
    assert alternatives_db.rows["venue_booking"][0]["status"] == status


def test_tc_007_layout_belongs_to_booking_without_overwriting_event(
    client, alternatives_db
):
    alternatives_db.rows["event"][0]["layout_requirements"] = "Organiser's original requirement"
    response = submit(client)
    assert response.status_code == 201
    assert response.get_json()["booking"].get("setup_layout") == "Banquet"
    assert alternatives_db.rows["venue_booking"][0].get("setup_layout") == "Banquet"
    assert alternatives_db.rows["event"][0]["layout_requirements"] == "Organiser's original requirement"
    assert not any(
        table == "event" and operation == "update"
        for table, operation, _ in alternatives_db.calls
    )


def test_tc_015_context_retains_each_alternative_period_layout_and_status(
    client, alternatives_db
):
    alternatives_db.rows["venue_booking"].extend(
        [
            active_booking(event_id="EVT-101", setup_layout="Banquet"),
            active_booking(
                booking_id="second",
                event_id="EVT-101",
                venue_id="VEN-002",
                requested_start="2026-11-16T13:00:00+08:00",
                requested_end="2026-11-16T16:00:00+08:00",
                setup_layout="Classroom",
                status="tentative",
            ),
        ]
    )
    response = client.get("/api/venue-bookings/context", headers=HEADERS)
    assert response.status_code == 200
    rows = response.get_json()["bookings"]
    assert [(r["booking_id"], r["setup_layout"], r["status"]) for r in rows] == [
        ("existing", "Banquet", "requested"),
        ("second", "Classroom", "tentative"),
    ]
    assert rows[0]["requested_start"] == START
    assert rows[0]["requested_end"] == END
    assert rows[1]["requested_start"] == "2026-11-16T13:00:00+08:00"
    assert rows[1]["requested_end"] == "2026-11-16T16:00:00+08:00"


def test_tc_002_availability_honours_authoritative_occupied_period_decision(
    client, alternatives_db
):
    # A false RPC decision can represent a buffer conflict or an RLS-hidden
    # commitment. Empty locally visible rows must not override that decision.
    alternatives_db.rpc.return_value.execute.return_value = SimpleNamespace(data=False)
    response = client.post(
        "/api/venue-bookings/availability",
        headers=HEADERS,
        json={key: value for key, value in PAYLOAD.items() if key != "venue_id"},
    )
    assert response.status_code == 200
    assert response.get_json()["venues"] == []
    assert alternatives_db.rpc.call_count >= 1
    for call in alternatives_db.rpc.call_args_list:
        name, params = call.args
        assert name == "cs_venue_period_available"
        assert params["p_start"] == START
        assert params["p_end"] == END


@pytest.mark.parametrize("next_start,available", [("12:29", False), ("12:30", True)])
def test_tc_009_availability_uses_rpc_for_half_hour_boundary(
    client, alternatives_db, next_start, available
):
    # PostgreSQL tests establish the actual buffer calculation. Here the route
    # must pass the chosen period through and honour the authoritative decision.
    alternatives_db.rows["venue_booking"].append(
        active_booking(status="confirmed", setup_layout="Theatre")
    )
    alternatives_db.rpc.return_value.execute.return_value = SimpleNamespace(data=available)
    response = client.post(
        "/api/venue-bookings/availability",
        headers=HEADERS,
        json={
            **{key: value for key, value in PAYLOAD.items() if key != "venue_id"},
            "start_time": next_start,
            "end_time": "14:00",
        },
    )
    assert response.status_code == 200
    assert [row["venue_id"] for row in response.get_json()["venues"]] == (
        ["VEN-001"] if available else []
    )
    alternatives_db.rpc.assert_called_once()
    name, params = alternatives_db.rpc.call_args.args
    assert name == "cs_venue_period_available"
    assert params["p_venue_id"] == "VEN-001"
    assert params["p_start"] == f"2026-11-15T{next_start}:00+08:00"
    assert params["p_end"] == "2026-11-15T14:00:00+08:00"


def test_tc_009_cancelled_blackout_does_not_block_submission(client, alternatives_db):
    alternatives_db.rows["venue_block"].append(
        {
            "venue_block_id": "cancelled-block",
            "venue_id": "VEN-001",
            "start_datetime": START,
            "end_datetime": END,
            "status": "cancelled",
        }
    )
    response = submit(client)
    assert response.status_code == 201
    assert len(alternatives_db.rows["venue_booking"]) == 1


@pytest.mark.parametrize("as_list", [False, True])
def test_tc_017_confirmation_delegates_to_atomic_rpc_and_returns_saved_row(
    client, alternatives_db, as_list
):
    alternatives_db.auth.get_user.return_value.user.id = "STAFF-1"
    original = active_booking(booking_id="selected", event_id="EVT-101", setup_layout="Banquet")
    alternatives_db.rows["venue_booking"].append(deepcopy(original))
    saved = {
        **original,
        "status": "confirmed",
        "decided_by": "STAFF-1",
        "decided_at": "2026-10-27T10:00:00+00:00",
    }
    alternatives_db.rpc.return_value.execute.return_value = SimpleNamespace(data=[deepcopy(saved)] if as_list else deepcopy(saved))
    response = client.post("/api/venue-bookings/selected/approve", headers=HEADERS)
    assert response.status_code == 200
    alternatives_db.rpc.assert_called_once_with(
        "confirm_venue_booking", {"p_booking_id": "selected"}
    )
    assert response.get_json()["booking"] == saved
    # No Python-side status writes: SQL owns confirmation and sibling cancellation.
    assert not any(
        table == "venue_booking" and operation == "update"
        for table, operation, _ in alternatives_db.calls
    )


def test_tc_018_rpc_conflict_does_not_return_success_or_mutate_pending_rows(
    client, alternatives_db
):
    alternatives_db.auth.get_user.return_value.user.id = "STAFF-1"
    alternatives_db.rows["venue_booking"].append(
        active_booking(booking_id="selected", event_id="EVT-101", setup_layout="Banquet")
    )
    before = deepcopy(alternatives_db.rows["venue_booking"])
    alternatives_db.rpc.return_value.execute.side_effect = APIError(
        {
            "code": "P0001",
            "message": "Venue is unavailable for the occupied period",
            "details": None,
            "hint": None,
        }
    )
    response = client.post("/api/venue-bookings/selected/approve", headers=HEADERS)
    assert response.status_code == 409
    assert response.get_json()["success"] is False
    assert "unavailable" in response.get_json()["error"].lower()
    assert alternatives_db.rows["venue_booking"] == before
    alternatives_db.rpc.assert_called_once_with(
        "confirm_venue_booking", {"p_booking_id": "selected"}
    )


def test_tc_019_repeat_confirmation_returns_existing_saved_result(
    client, alternatives_db
):
    alternatives_db.auth.get_user.return_value.user.id = "STAFF-1"
    saved = active_booking(
        booking_id="selected",
        event_id="EVT-101",
        status="confirmed",
        setup_layout="Banquet",
        decided_by="STAFF-1",
        decided_at="2026-10-27T10:00:00+00:00",
    )
    alternatives_db.rows["venue_booking"].append(deepcopy(saved))
    alternatives_db.rpc.return_value.execute.return_value = SimpleNamespace(data=deepcopy(saved))
    response = client.post("/api/venue-bookings/selected/approve", headers=HEADERS)
    assert response.status_code == 200
    assert response.get_json()["booking"] == saved
    assert alternatives_db.rows["venue_booking"] == [saved]


@pytest.mark.parametrize("data", [None, 1, [], "true"])
def test_unknown_availability_never_appears_bookable(client, alternatives_db, data):
    alternatives_db.rpc.return_value.execute.return_value = SimpleNamespace(data=data)
    assert submit(client).status_code == 503
    assert alternatives_db.rows["venue_booking"] == []


@pytest.mark.parametrize("code,message,status", [
    ("P0001", "B1_CONFIGURATION_REQUIRED", 409),
    ("PGRST202", "RPC missing", 503),
    ("42501", "Private permission diagnostic", 403),
    ("P0001", "Private diagnostic with database internals", 503),
])
def test_availability_errors_are_clear_and_sanitised(client, alternatives_db, code, message, status):
    alternatives_db.rpc.return_value.execute.side_effect = APIError({"code": code, "message": message})
    response = submit(client)
    assert response.status_code == status
    assert "Private" not in response.get_json()["error"]
    assert alternatives_db.rows["venue_booking"] == []


def test_submission_trigger_conflict_is_reported_without_optimistic_success(client, alternatives_db, monkeypatch):
    original = Query.execute
    def execute(query):
        if query.table == "venue_booking" and query.operation == "insert":
            raise APIError({"code": "P0001", "message": "Venue is unavailable for the occupied period"})
        return original(query)
    monkeypatch.setattr(Query, "execute", execute)
    response = submit(client)
    assert response.status_code == 409
    assert "unavailable" in response.get_json()["error"]
    assert alternatives_db.rows["venue_booking"] == []


def test_cancelled_alternatives_do_not_leave_venue_outstanding(alternatives_db, monkeypatch):
    from app.services import event_service
    from app.services.track_readiness_actions_service import _evaluate_venue
    bookings = [{"status": "confirmed"}, {"status": "cancelled"}, {"status": "rejected"}]
    event = alternatives_db.rows["event"][0]
    event.update(organiser_id="OWNER-1", venue_booking=bookings)
    monkeypatch.setattr(event_service, "supabase", alternatives_db)
    result, error = event_service.get_event_details_for_organiser("EVT-101", "OWNER-1")
    assert error is None
    assert result["outstanding_arrangements"] == []
    assert result["status"] == "planning"
    condition, actions = _evaluate_venue(bookings)
    assert condition["complete"] is True
    assert actions == []
