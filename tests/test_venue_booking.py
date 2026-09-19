from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.venue_booking_service import submit_venue_booking_request, VenueBookingError


HEADERS = {"Authorization": "Bearer test-token"}
PAYLOAD = {
    "event_id": "EVT-101", "venue_id": "VEN-001",
    "booking_date": "2026-11-15", "start_time": "09:00", "end_time": "12:00",
    "setup_layout": "Banquet",
}


class Query:
    """Evaluate filters against rows instead of returning prewritten query results.

    This models the current service contract; it does not verify the live schema/RLS.
    """

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
            new = self.payload if isinstance(self.payload, list) else [self.payload]
            new = [{"id": f"generated-{len(rows) + i}", **row} for i, row in enumerate(new)]
            rows.extend(new)
            return SimpleNamespace(data=deepcopy(new))
        selected = [row for row in rows if all(check(row) for check in self.filters)]
        if self.operation == "update":
            for row in selected:
                row.update(self.payload)
        return SimpleNamespace(data=deepcopy(selected))


class Database:
    def __init__(self):
        self.rows = {
            "event": [{"event_id": "EVT-101", "status": "planning"}],
            "venue_booking": [], "venue_block": [], "notification": [],
            "user_role": [
                {"user_id": "COORD-1", "role": "event_coordinator"},
                {"user_id": "STAFF-1", "role": "venue_staff"},
            ],
            "venue": [{"id": "VEN-001", "capacity": 100}],
        }
        self.calls, self.failures = [], set()
        self.auth = MagicMock()
        self.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="COORD-1"))

    def table(self, name):
        return Query(self, name)


@pytest.fixture
def client():
    # Real application registration is part of every route test.
    return app.test_client()


@pytest.fixture
def database():
    db = Database()
    with patch("app.services.venue_booking_service.create_authenticated_supabase_client", return_value=db) as factory:
        db.factory = factory
        yield db


def submit(client, payload=None):
    return client.post("/api/venue-bookings", json=PAYLOAD if payload is None else payload, headers=HEADERS)


def test_tc_001_success_creates_linked_hold_and_pending_status(client, database):
    response = submit(client)
    assert response.status_code == 201
    data = response.get_json()
    database.factory.assert_called_once_with("test-token")
    database.auth.get_user.assert_called_once_with("test-token")
    assert database.rows["venue_booking"] == [{
        "id": "generated-0", **PAYLOAD, "setup_notes": None, "status": "requested",
    }]
    assert data["booking"] == database.rows["venue_booking"][0]
    assert data["display_status"] == "Pending Venue Approval"
    # Assignment-specific notification delivery still requires the actual schema.
    assert len(database.rows["notification"]) == 1
    assert database.rows["notification"][0]["user_id"] == "STAFF-1"


@pytest.mark.parametrize("status", ["requested", "tentative", "confirmed"])
@pytest.mark.parametrize("start,end", [("08:00", "10:00"), ("10:00", "13:00"), ("08:00", "13:00"), ("10:00", "11:00"), ("09:00", "12:00")])
def test_tc_002_overlapping_booking_prevents_insert(client, database, status, start, end):
    database.rows["venue_booking"].append({**PAYLOAD, "id": "existing", "event_id": "OTHER", "status": status, "start_time": start, "end_time": end})
    response = submit(client)
    assert response.status_code == 409
    assert len(database.rows["venue_booking"]) == 1
    assert database.rows["notification"] == []


def test_tc_002_blackout_prevents_insert(client, database):
    database.rows["venue_block"].append({"venue_id": "VEN-001", "block_date": "2026-11-15", "start_time": "10:00", "end_time": "13:00"})
    assert submit(client).status_code == 409
    assert database.rows["venue_booking"] == []
    assert database.rows["notification"] == []


@pytest.mark.parametrize("status", ["draft", "requested", "changes_requested", "confirmed", "completed", "cancelled", "withdrawn", "rejected", "approved"])
def test_tc_003_only_planning_events_can_be_booked(client, database, status):
    database.rows["event"][0]["status"] = status
    assert submit(client).status_code == 400
    assert database.rows["venue_booking"] == []
    assert database.rows["notification"] == []


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


@pytest.mark.parametrize("body,content_type", [('null', 'application/json'), ('{', 'application/json'), ('text', 'text/plain')])
def test_malformed_or_missing_object_is_rejected(client, database, body, content_type):
    response = client.post("/api/venue-bookings", data=body, content_type=content_type, headers=HEADERS)
    assert response.status_code == 400
    database.factory.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"booking_date": "2026-02-30"}, {"booking_date": "20261115"},
    {"start_time": "24:00"}, {"start_time": "09:00+08:00"},
    {"start_time": "12:00"}, {"start_time": "13:00"}, {"setup_notes": []},
])
def test_invalid_dates_times_and_notes(client, database, changes):
    assert submit(client, {**PAYLOAD, **changes}).status_code == 400
    database.factory.assert_not_called()


@pytest.mark.parametrize("method,url", [
    ("post", "/api/venue-bookings"), ("get", "/api/venue-bookings"),
    ("post", "/api/venue-bookings/booking/approve"), ("post", "/api/venue-bookings/booking/reject"),
    ("post", "/api/venues/venue/block"), ("put", "/api/venues/venue"), ("get", "/api/venues/venue/schedule"),
])
def test_all_venue_routes_require_authentication(client, database, method, url):
    assert getattr(client, method)(url, json={}).status_code == 401
    database.factory.assert_not_called()


def test_invalid_session_is_rejected(client, database):
    database.auth.get_user.side_effect = RuntimeError("expired token")
    assert submit(client).status_code == 401
    assert database.rows["venue_booking"] == []


def test_non_coordinator_cannot_submit(client, database):
    database.rows["user_role"][0]["role"] = "event_organiser"
    assert submit(client).status_code == 403
    assert database.rows["venue_booking"] == []


def test_coordinator_cannot_approve(client, database):
    response = client.post("/api/venue-bookings/booking/approve", headers=HEADERS)
    assert response.status_code == 403


def test_event_missing_or_hidden_by_rls(client, database):
    database.rows["event"] = []
    assert submit(client).status_code == 404
    assert database.rows["venue_booking"] == []


@pytest.mark.parametrize("status", ["requested", "tentative", "confirmed"])
def test_event_cannot_have_second_active_arrangement(client, database, status):
    database.rows["venue_booking"].append({**PAYLOAD, "id": "existing", "venue_id": "OTHER", "status": status})
    assert submit(client).status_code == 409
    assert len(database.rows["venue_booking"]) == 1


@pytest.mark.parametrize("start,end", [("07:00", "09:00"), ("12:00", "14:00")])
def test_back_to_back_bookings_are_allowed(client, database, start, end):
    database.rows["venue_booking"].append({**PAYLOAD, "id": "existing", "event_id": "OTHER", "status": "confirmed", "start_time": start, "end_time": end})
    assert submit(client).status_code == 201


@pytest.mark.parametrize("status", ["rejected", "cancelled"])
def test_inactive_booking_does_not_block_submission(client, database, status):
    database.rows["venue_booking"].append({**PAYLOAD, "id": "existing", "status": status})
    assert submit(client).status_code == 201


def test_database_failure_is_sanitised(client, database):
    database.failures.add(("venue_booking", "insert"))
    response = submit(client)
    assert response.status_code == 503
    assert "private" not in response.get_json()["error"]
    assert database.rows["notification"] == []


def test_notification_failure_reports_saved_booking_without_duplicate_on_retry(client, database):
    database.failures.add(("notification", "insert"))
    response = submit(client)
    assert response.status_code == 201
    assert response.get_json()["notification_sent"] is False
    assert "Do not resubmit" in response.get_json()["warning"]
    assert len(database.rows["venue_booking"]) == 1
    assert submit(client).status_code == 409
    assert len(database.rows["venue_booking"]) == 1


def test_service_validates_direct_calls(database):
    with pytest.raises(VenueBookingError):
        submit_venue_booking_request("test-token", **{**PAYLOAD, "end_time": "08:00"})
    database.factory.assert_not_called()


@pytest.mark.parametrize("status", ["requested", "tentative"])
def test_staff_approval_uses_supported_confirmed_status(client, database, status):
    database.auth.get_user.return_value.user.id = "STAFF-1"
    database.rows["venue_booking"].append({**PAYLOAD, "id": "booking", "status": status})
    response = client.post("/api/venue-bookings/booking/approve", headers=HEADERS)
    assert response.status_code == 200
    assert database.rows["venue_booking"][0]["status"] == "confirmed"


@pytest.mark.parametrize("action", ["approve", "reject"])
@pytest.mark.parametrize("status", ["confirmed", "rejected", "cancelled"])
def test_final_booking_cannot_be_decided_again(client, database, action, status):
    database.auth.get_user.return_value.user.id = "STAFF-1"
    database.rows["venue_booking"].append({**PAYLOAD, "id": "booking", "status": status})
    response = client.post(f"/api/venue-bookings/booking/{action}", headers=HEADERS, json={})
    assert response.status_code in (400, 409)
    assert database.rows["venue_booking"][0]["status"] == status
