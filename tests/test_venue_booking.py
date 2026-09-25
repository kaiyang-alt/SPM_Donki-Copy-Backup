from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.venue_booking_service import VenueBookingError, submit_venue_booking_request


HEADERS = {"Authorization": "Bearer test-token"}
PAYLOAD = {
    "event_id": "EVT-101",
    "venue_id": "VEN-001",
    "booking_date": "2026-11-15",
    "start_time": "09:00",
    "end_time": "12:00",
    "setup_layout": "Banquet",
}
START = "2026-11-15T09:00:00+08:00"
END = "2026-11-15T12:00:00+08:00"


class Query:
    """Small in-memory Supabase query model using the checked-in live schema."""

    def __init__(self, database, table):
        self.database, self.table = database, table
        self.filters = []
        self.operation, self.payload = "select", None

    def select(self, columns):
        self.database.calls.append((self.table, "select", columns))
        return self

    def eq(self, column, value):
        self.filters.append(lambda row: row.get(column) == value)
        return self

    def neq(self, column, value):
        self.filters.append(lambda row: row.get(column) != value)
        return self

    def in_(self, column, values):
        self.filters.append(lambda row: row.get(column) in values)
        return self

    def lt(self, column, value):
        self.filters.append(lambda row: row[column] < value)
        return self

    def gt(self, column, value):
        self.filters.append(lambda row: row[column] > value)
        return self

    def insert(self, payload):
        self.operation, self.payload = "insert", deepcopy(payload)
        return self

    def update(self, payload):
        self.operation, self.payload = "update", deepcopy(payload)
        return self

    def execute(self):
        self.database.calls.append((self.table, self.operation, self.payload))
        if (self.table, self.operation) in self.database.failures:
            raise RuntimeError("Database error with private diagnostic details")
        rows = self.database.rows[self.table]
        if self.operation == "insert":
            new_rows = self.payload if isinstance(self.payload, list) else [self.payload]
            primary_key = {
                "venue_booking": "booking_id",
                "venue_block": "venue_block_id",
            }.get(self.table, "id")
            new_rows = [
                {primary_key: f"generated-{len(rows) + index}", **row}
                for index, row in enumerate(new_rows)
            ]
            rows.extend(new_rows)
            return SimpleNamespace(data=deepcopy(new_rows))
        selected = [row for row in rows if all(check(row) for check in self.filters)]
        if self.operation == "update":
            for row in selected:
                row.update(self.payload)
        return SimpleNamespace(data=deepcopy(selected))


class Database:
    def __init__(self):
        self.rows = {
            "event": [
                {
                    "event_id": "EVT-101",
                    "coordinator_id": "COORD-1",
                    "name": "Conference",
                    "status": "planning",
                    "expected_attendance": 80,
                    "layout_requirements": None,
                }
            ],
            "venue": [
                {
                    "venue_id": "VEN-001",
                    "name": "Grand Hall",
                    "capacity": 100,
                    "supported_layouts": ["Banquet", "Theatre"],
                    "active": True,
                }
            ],
            "venue_booking": [],
            "venue_block": [],
            "notification": [],
            "user_role": [
                {"user_id": "COORD-1", "role": "event_coordinator"},
                {"user_id": "STAFF-1", "role": "venue_staff"},
            ],
        }
        self.calls, self.failures = [], set()
        self.auth = MagicMock()
        self.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="COORD-1"))

    def table(self, name):
        return Query(self, name)


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def database():
    db = Database()
    with patch(
        "app.services.venue_booking_service.create_authenticated_supabase_client",
        return_value=db,
    ) as factory:
        db.factory = factory
        yield db


def submit(client, payload=None):
    return client.post(
        "/api/venue-bookings",
        json=PAYLOAD if payload is None else payload,
        headers=HEADERS,
    )


def active_booking(**changes):
    row = {
        "booking_id": "existing",
        "event_id": "OTHER",
        "venue_id": "VEN-001",
        "requested_start": START,
        "requested_end": END,
        "requested_by": "COORD-2",
        "status": "requested",
    }
    row.update(changes)
    return row


def test_tc_001_success_uses_live_schema_and_persists_layout(client, database):
    response = submit(client)
    assert response.status_code == 201
    data = response.get_json()
    booking = database.rows["venue_booking"][0]
    assert booking["event_id"] == "EVT-101"
    assert booking["venue_id"] == "VEN-001"
    assert booking["requested_start"] == START
    assert booking["requested_end"] == END
    assert booking["requested_by"] == "COORD-1"
    assert booking["status"] == "requested"
    assert "booking_date" not in booking
    assert "setup_layout" not in booking
    assert database.rows["event"][0]["layout_requirements"] == "Banquet"
    assert data["display_status"] == "Pending Venue Approval"
    assert data["notification_sent"] is False
    assert "warning" in data


def test_context_returns_only_assigned_planning_events_and_saved_bookings(client, database):
    database.rows["venue_booking"].append(active_booking(event_id="EVT-101"))
    response = client.get("/api/venue-bookings/context", headers=HEADERS)
    assert response.status_code == 200
    data = response.get_json()
    assert [event["event_id"] for event in data["events"]] == ["EVT-101"]
    assert [venue["venue_id"] for venue in data["venues"]] == ["VEN-001"]
    assert [booking["booking_id"] for booking in data["bookings"]] == ["existing"]


def test_availability_filters_capacity_layout_and_conflicts(client, database):
    database.rows["venue"].extend(
        [
            {"venue_id": "SMALL", "capacity": 20, "supported_layouts": ["Banquet"], "active": True},
            {"venue_id": "WRONG", "capacity": 100, "supported_layouts": ["Theatre"], "active": True},
            {"venue_id": "INACTIVE", "capacity": 100, "supported_layouts": ["Banquet"], "active": False},
            {"venue_id": "BUSY", "capacity": 100, "supported_layouts": ["Banquet"], "active": True},
        ]
    )
    database.rows["venue_booking"].append(active_booking(venue_id="BUSY"))
    response = client.post(
        "/api/venue-bookings/availability",
        headers=HEADERS,
        json={key: value for key, value in PAYLOAD.items() if key != "venue_id"},
    )
    assert response.status_code == 200
    assert [venue["venue_id"] for venue in response.get_json()["venues"]] == ["VEN-001"]


@pytest.mark.parametrize("status", ["requested", "tentative", "confirmed"])
@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-11-15T08:00:00+08:00", "2026-11-15T10:00:00+08:00"),
        ("2026-11-15T10:00:00+08:00", "2026-11-15T13:00:00+08:00"),
        ("2026-11-15T08:00:00+08:00", "2026-11-15T13:00:00+08:00"),
        ("2026-11-15T10:00:00+08:00", "2026-11-15T11:00:00+08:00"),
        (START, END),
    ],
)
def test_tc_002_overlapping_booking_prevents_insert(client, database, status, start, end):
    database.rows["venue_booking"].append(
        active_booking(status=status, requested_start=start, requested_end=end)
    )
    assert submit(client).status_code == 409
    assert len(database.rows["venue_booking"]) == 1


def test_tc_002_blackout_prevents_insert(client, database):
    database.rows["venue_block"].append(
        {
            "venue_block_id": "BLOCK-1",
            "venue_id": "VEN-001",
            "start_datetime": "2026-11-15T10:00:00+08:00",
            "end_datetime": "2026-11-15T13:00:00+08:00",
        }
    )
    assert submit(client).status_code == 409
    assert database.rows["venue_booking"] == []


@pytest.mark.parametrize(
    "status",
    ["draft", "requested", "changes_requested", "confirmed", "completed", "cancelled", "withdrawn", "rejected"],
)
def test_tc_003_only_planning_events_can_be_booked(client, database, status):
    database.rows["event"][0]["status"] = status
    assert submit(client).status_code == 400
    assert database.rows["venue_booking"] == []


def test_event_must_be_assigned_to_coordinator(client, database):
    database.rows["event"][0]["coordinator_id"] = "OTHER"
    assert submit(client).status_code == 404


@pytest.mark.parametrize("field", list(PAYLOAD))
@pytest.mark.parametrize("value", [None, "", "   ", [], 123, True])
def test_tc_004_invalid_required_fields(client, database, field, value):
    assert submit(client, {**PAYLOAD, field: value}).status_code == 400
    database.factory.assert_not_called()


@pytest.mark.parametrize("field", list(PAYLOAD))
def test_tc_004_missing_required_fields(client, database, field):
    payload = {key: value for key, value in PAYLOAD.items() if key != field}
    assert submit(client, payload).status_code == 400
    database.factory.assert_not_called()


@pytest.mark.parametrize("payload", [["invalid"], "invalid", 42, True, []])
def test_non_object_json_is_rejected(client, database, payload):
    assert submit(client, payload).status_code == 400
    database.factory.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"booking_date": "2026-02-30"},
        {"booking_date": "20261115"},
        {"start_time": "24:00"},
        {"start_time": "09:00+08:00"},
        {"start_time": "12:00"},
        {"start_time": "13:00"},
    ],
)
def test_invalid_dates_and_times(client, database, changes):
    assert submit(client, {**PAYLOAD, **changes}).status_code == 400
    database.factory.assert_not_called()


@pytest.mark.parametrize(
    "method,url",
    [
        ("post", "/api/venue-bookings"),
        ("get", "/api/venue-bookings"),
        ("get", "/api/venue-bookings/context"),
        ("get", "/api/venue-staff/context"),
        ("post", "/api/venue-bookings/availability"),
        ("post", "/api/venue-bookings/booking/approve"),
        ("post", "/api/venue-bookings/booking/reject"),
        ("post", "/api/venues/venue/block"),
        ("put", "/api/venues/venue"),
        ("get", "/api/venues/venue/schedule"),
    ],
)
def test_all_venue_routes_require_authentication(client, database, method, url):
    assert getattr(client, method)(url, json={}).status_code == 401
    database.factory.assert_not_called()


def test_invalid_session_is_rejected(client, database):
    database.auth.get_user.side_effect = RuntimeError("expired token")
    assert submit(client).status_code == 401


def test_non_coordinator_cannot_submit(client, database):
    database.rows["user_role"][0]["role"] = "event_organiser"
    assert submit(client).status_code == 403


@pytest.mark.parametrize("status", ["requested", "tentative", "confirmed"])
def test_event_cannot_have_second_active_arrangement(client, database, status):
    database.rows["venue_booking"].append(
        active_booking(event_id="EVT-101", venue_id="OTHER", status=status)
    )
    assert submit(client).status_code == 409


@pytest.mark.parametrize(
    "start,end",
    [
        ("2026-11-15T07:00:00+08:00", START),
        (END, "2026-11-15T14:00:00+08:00"),
    ],
)
def test_back_to_back_bookings_are_allowed(client, database, start, end):
    database.rows["venue_booking"].append(
        active_booking(requested_start=start, requested_end=end, status="confirmed")
    )
    assert submit(client).status_code == 201


@pytest.mark.parametrize("status", ["rejected", "cancelled"])
def test_inactive_booking_does_not_block_submission(client, database, status):
    database.rows["venue_booking"].append(active_booking(status=status))
    assert submit(client).status_code == 201


def test_venue_must_be_active(client, database):
    database.rows["venue"][0]["active"] = False
    assert submit(client).status_code == 404


def test_venue_must_have_capacity(client, database):
    database.rows["venue"][0]["capacity"] = 79
    assert submit(client).status_code == 409


def test_venue_must_support_layout(client, database):
    database.rows["venue"][0]["supported_layouts"] = ["Theatre"]
    assert submit(client).status_code == 409


def test_database_failure_is_sanitised(client, database):
    database.failures.add(("venue_booking", "insert"))
    response = submit(client)
    assert response.status_code == 503
    assert "private" not in response.get_json()["error"]


def test_service_validates_direct_calls(database):
    with pytest.raises(VenueBookingError):
        submit_venue_booking_request("test-token", **{**PAYLOAD, "end_time": "08:00"})
    database.factory.assert_not_called()


@pytest.mark.parametrize("status", ["requested", "tentative"])
def test_staff_approval_uses_confirmed_status_and_audit_fields(client, database, status):
    database.auth.get_user.return_value.user.id = "STAFF-1"
    database.rows["venue_booking"].append(active_booking(booking_id="booking", status=status))
    response = client.post("/api/venue-bookings/booking/approve", headers=HEADERS)
    assert response.status_code == 200
    booking = database.rows["venue_booking"][0]
    assert booking["status"] == "confirmed"
    assert booking["decided_by"] == "STAFF-1"
    assert booking["decided_at"]


def test_staff_rejection_stores_reason_and_alternatives_as_text(client, database):
    database.auth.get_user.return_value.user.id = "STAFF-1"
    database.rows["venue_booking"].append(active_booking(booking_id="booking"))
    response = client.post(
        "/api/venue-bookings/booking/reject",
        headers=HEADERS,
        json={"reason": "Unavailable", "alternative_venue_ids": ["VEN-002", "VEN-003"]},
    )
    assert response.status_code == 200
    assert database.rows["venue_booking"][0]["decision_reason"] == (
        "Reason: Unavailable\nSuggested alternatives: VEN-002, VEN-003"
    )


@pytest.mark.parametrize("action", ["approve", "reject"])
@pytest.mark.parametrize("status", ["confirmed", "rejected", "cancelled"])
def test_final_booking_cannot_be_decided_again(client, database, action, status):
    database.auth.get_user.return_value.user.id = "STAFF-1"
    database.rows["venue_booking"].append(active_booking(booking_id="booking", status=status))
    response = client.post(
        f"/api/venue-bookings/booking/{action}", headers=HEADERS, json={}
    )
    assert response.status_code == 409
    assert database.rows["venue_booking"][0]["status"] == status


def test_venue_block_uses_schema_and_staff_audit_fields(client, database):
    database.auth.get_user.return_value.user.id = "STAFF-1"
    response = client.post(
        "/api/venues/VEN-001/block",
        headers=HEADERS,
        json={
            "block_date": "2026-11-16",
            "start_time": "09:00",
            "end_time": "10:00",
            "reason": "Maintenance",
        },
    )
    assert response.status_code == 201
    block = database.rows["venue_block"][0]
    assert block["start_datetime"] == "2026-11-16T09:00:00+08:00"
    assert block["created_by"] == "STAFF-1"


def test_venue_update_uses_live_schema_columns(client, database):
    database.auth.get_user.return_value.user.id = "STAFF-1"
    response = client.put(
        "/api/venues/VEN-001",
        headers=HEADERS,
        json={
            "capacity": 120,
            "supported_layouts": ["Banquet", "Classroom"],
            "accessibility": "Step-free access",
        },
    )
    assert response.status_code == 200
    venue = database.rows["venue"][0]
    assert venue["capacity"] == 120
    assert venue["supported_layouts"] == ["Banquet", "Classroom"]
    assert venue["accessibility"] == "Step-free access"
