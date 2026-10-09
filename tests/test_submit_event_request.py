from types import SimpleNamespace

import pytest
from flask import Flask

from app.routes import submit_event_request_routes as routes
from app.services import submit_event_request_service as service


class FakeQuery:
    def __init__(self, data, log):
        self._data = data
        self._log = log

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self._log.append((name, args, kwargs))
            return self
        return method

    def execute(self):
        return SimpleNamespace(data=self._data)


class FakeClient:
    def __init__(self, tables):
        self.tables = tables
        self.log = []

    def table(self, name):
        self.log.append(("table", (name,), {}))
        return FakeQuery(self.tables.get(name, []), self.log)

    def _first(self, op):
        return next((a[0] for n, a, _ in self.log if n == op), None)

    def inserted_row(self):
        return self._first("insert")

    def updated_row(self):
        return self._first("update")


ORGANISER = [{"user_id": "u1", "role": "event_organiser"}]

# 20 Nov 2026, 09:00-17:00 in Singapore (UTC+8) is 01:00-09:00 UTC.
FULL = {
    "name": "Regional Business Conference 2026",
    "description": "A one-day conference for regional business leaders.",
    "purpose": "Share industry developments and encourage professional networking.",
    "preferred_start_datetime": "2026-11-20T01:00:00.000Z",
    "preferred_end_datetime": "2026-11-20T09:00:00.000Z",
    "expected_attendance": "150",
    "venue_requirements": "Indoor venue",
    "layout_requirements": "Theatre layout",
    "accessibility_needs": "Step-free access; accessible seating",
    "technical_support_required": True,
    "technical_requirements": "Projector, microphones, and presentation support",
    "registration_enabled": True,
}


def client_returning(event_rows):
    return FakeClient({"user_role": ORGANISER, "event": event_rows})


# TC-002
def test_submit_complete_request_sets_requested_status():
    client = client_returning([{"event_id": "e1", "status": "requested", "name": FULL["name"]}])
    result = service.submit_request(client, "u1", FULL)
    row = client.inserted_row()
    assert row["status"] == "requested"
    assert row["organiser_id"] == "u1"
    assert row["expected_attendance"] == 150
    assert row["preferred_start_datetime"] == "2026-11-20T01:00:00+00:00"
    assert row["preferred_end_datetime"] == "2026-11-20T09:00:00+00:00"
    assert row["created_at"] and row["updated_at"]
    assert "start_datetime" not in row and "end_datetime" not in row
    assert result["status"] == "requested"


# TC-003
@pytest.mark.parametrize(
    "omitted",
    ["expected_attendance", "preferred_start_datetime", "preferred_end_datetime", "name"],
)
def test_submit_blocked_when_mandatory_field_missing(omitted):
    client = client_returning([{"event_id": "e1"}])
    with pytest.raises(service.EventRequestError) as exc:
        service.submit_request(client, "u1", {**FULL, omitted: ""})
    assert exc.value.status_code == 422
    assert omitted in [m["field"] for m in exc.value.missing_fields]
    assert client.inserted_row() is None and client.updated_row() is None


def test_submit_blocked_when_date_and_time_absent_entirely():
    client = client_returning([])
    data = {k: v for k, v in FULL.items() if not k.startswith("preferred_")}
    with pytest.raises(service.EventRequestError) as exc:
        service.submit_request(client, "u1", data)
    fields = [m["field"] for m in exc.value.missing_fields]
    assert "preferred_start_datetime" in fields and "preferred_end_datetime" in fields


# TC-001
def test_save_incomplete_draft_uses_draft_status():
    client = client_returning([{"event_id": "e1", "status": "draft", "name": FULL["name"]}])
    result = service.save_draft(
        client, "u1", {"name": FULL["name"], "description": "A conference for regional business leaders."}
    )
    row = client.inserted_row()
    assert row["status"] == "draft"
    assert row["preferred_start_datetime"] is None
    assert row["preferred_end_datetime"] is None
    assert result["status"] == "draft"


def test_update_existing_draft_retains_modified_description():
    new_desc = "A one-day conference for regional business leaders and industry partners."
    client = client_returning([{"event_id": "e1", "status": "draft", "description": new_desc}])
    result = service.save_draft(
        client, "u1", {"event_id": "e1", "name": FULL["name"], "description": new_desc}
    )
    assert client.updated_row()["description"] == new_desc
    assert result["description"] == new_desc
    assert "created_at" not in client.updated_row()


def test_submit_existing_draft_updates_status_to_requested():
    client = client_returning([{"event_id": "e1", "status": "requested"}])
    service.submit_request(client, "u1", {**FULL, "event_id": "e1"})
    assert client.updated_row()["status"] == "requested"


def test_update_of_non_draft_event_is_rejected():
    client = client_returning([])  # update matched no draft row
    with pytest.raises(service.EventRequestError) as exc:
        service.save_draft(client, "u1", {"event_id": "e1", "name": "x"})
    assert exc.value.status_code == 404


def test_end_time_must_be_after_start_time():
    client = client_returning([])
    data = {**FULL, "preferred_end_datetime": "2026-11-20T00:00:00Z"}
    with pytest.raises(service.EventRequestError) as exc:
        service.submit_request(client, "u1", data)
    assert "preferred_end_datetime" in [m["field"] for m in exc.value.invalid_fields]


def test_invalid_datetime_rejected():
    client = client_returning([])
    with pytest.raises(service.EventRequestError) as exc:
        service.save_draft(client, "u1", {"name": "x", "preferred_start_datetime": "not-a-date"})
    assert "preferred_start_datetime" in [m["field"] for m in exc.value.invalid_fields]


def test_invalid_attendance_rejected():
    client = client_returning([])
    with pytest.raises(service.EventRequestError) as exc:
        service.submit_request(client, "u1", {**FULL, "expected_attendance": "abc"})
    assert "expected_attendance" in [m["field"] for m in exc.value.invalid_fields]


def test_non_organiser_is_rejected():
    client = FakeClient({"user_role": [], "event": []})
    with pytest.raises(service.EventRequestError) as exc:
        service.submit_request(client, "u1", FULL)
    assert exc.value.status_code == 403


# Route-level checks
@pytest.fixture
def http_client(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(routes.event_request_bp)
    fake = client_returning([{"event_id": "e1", "status": "requested"}])
    monkeypatch.setattr(routes, "_authenticate", lambda: (fake, "u1"))
    return app.test_client()


def test_submit_route_returns_confirmation_and_status(http_client):
    res = http_client.post("/api/event-requests/submit", json=FULL)
    assert res.status_code == 201
    body = res.get_json()
    assert "submitted successfully" in body["message"]
    assert body["event"]["status"] == "requested"


def test_submit_route_returns_missing_fields(http_client):
    res = http_client.post("/api/event-requests/submit", json={**FULL, "name": ""})
    assert res.status_code == 422
    assert res.get_json()["missing_fields"][0]["field"] == "name"


def test_route_requires_authentication():
    app = Flask(__name__)
    app.register_blueprint(routes.event_request_bp)
    res = app.test_client().get("/api/event-requests")
    assert res.status_code == 401