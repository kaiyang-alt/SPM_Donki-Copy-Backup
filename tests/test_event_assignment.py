import pytest
from flask import Flask

from app.routes import event_assignment_routes as routes
from app.services import event_assignment_service as service


# ---------- Fake Supabase client (no network) ----------

class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        rows = [
            row for row in self._rows
            if all(row.get(column) == value for column, value in self._filters)
        ]
        return FakeResponse(rows)


class FakeClient:
    def __init__(self, tables):
        self._tables = tables

    def table(self, name):
        return FakeQuery(self._tables.get(name, []))


COORDINATOR_ID = "11111111-1111-1111-1111-111111111111"
OTHER_COORDINATOR_ID = "22222222-2222-2222-2222-222222222222"
ORGANISER_ID = "33333333-3333-3333-3333-333333333333"
OUTSIDER_ID = "44444444-4444-4444-4444-444444444444"
EVENT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
UNASSIGNED_EVENT_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


@pytest.fixture
def fake_client():
    return FakeClient({
        "user_role": [
            {"user_id": COORDINATOR_ID, "role": "event_coordinator"},
            {"user_id": OTHER_COORDINATOR_ID, "role": "event_coordinator"},
            {"user_id": ORGANISER_ID, "role": "event_organiser"},
        ],
        "profile": [
            {"user_id": COORDINATOR_ID, "name": "Maya Tan"},
        ],
        "event": [
            {
                "event_id": EVENT_ID,
                "name": "Northstar Industry Forum",
                "status": "planning",
                "organiser_id": ORGANISER_ID,
                "coordinator_id": COORDINATOR_ID,
                "preferred_start_datetime": "2026-11-20T09:00:00+08:00",
                "preferred_end_datetime": "2026-11-20T17:00:00+08:00",
                "start_datetime": None,
                "end_datetime": None,
                "expected_attendance": 150,
            },
            {
                "event_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "name": "Harbor Research Symposium",
                "status": "planning",
                "organiser_id": ORGANISER_ID,
                "coordinator_id": OTHER_COORDINATOR_ID,
                "preferred_start_datetime": "2026-12-01T09:00:00+08:00",
                "preferred_end_datetime": "2026-12-01T12:00:00+08:00",
                "start_datetime": None,
                "end_datetime": None,
                "expected_attendance": 80,
            },
            {
                "event_id": UNASSIGNED_EVENT_ID,
                "name": "Lakeside Sustainability Workshop",
                "status": "requested",
                "organiser_id": ORGANISER_ID,
                "coordinator_id": None,
            },
        ],
    })


# ---------- Service tests ----------

def test_coordinator_sees_only_their_assigned_events(fake_client):
    events = service.get_assigned_events(fake_client, COORDINATOR_ID)

    assert [e["name"] for e in events] == ["Northstar Industry Forum"]
    assert events[0]["status"] == "planning"
    assert events[0]["start"] == "2026-11-20T09:00:00+08:00"


def test_non_coordinator_cannot_view_assigned_events(fake_client):
    with pytest.raises(service.PermissionDeniedError):
        service.get_assigned_events(fake_client, ORGANISER_ID)


def test_organiser_sees_coordinator_assigned(fake_client):
    result = service.get_event_assignment(fake_client, ORGANISER_ID, EVENT_ID)

    assert result["coordinator_assigned"] is True
    assert result["status"] == "planning"
    assert "coordinator_id" not in result

def test_organiser_sees_assigned_coordinator_name(fake_client):
    result = service.get_event_assignment(fake_client, ORGANISER_ID, EVENT_ID)

    assert result["coordinator_name"] == "Maya Tan"

def test_coordinator_name_missing_when_profile_not_visible(fake_client):
    fake_client._tables["profile"] = []  # simulates RLS hiding the profile

    result = service.get_event_assignment(fake_client, ORGANISER_ID, EVENT_ID)

    assert result["coordinator_assigned"] is True
    assert result["coordinator_name"] is None


def test_organiser_sees_awaiting_assignment(fake_client):
    result = service.get_event_assignment(fake_client, ORGANISER_ID, UNASSIGNED_EVENT_ID)

    assert result["coordinator_assigned"] is False
    assert result["status"] == "requested"


def test_unrelated_user_cannot_view_event_assignment(fake_client):
    with pytest.raises(service.PermissionDeniedError):
        service.get_event_assignment(fake_client, OUTSIDER_ID, EVENT_ID)


def test_missing_event_raises_not_found(fake_client):
    with pytest.raises(service.EventNotFoundError):
        service.get_event_assignment(
            fake_client, ORGANISER_ID, "dddddddd-dddd-dddd-dddd-dddddddddddd"
        )


# ---------- Route tests ----------

@pytest.fixture
def client(monkeypatch, fake_client):
    app = Flask(__name__)
    app.register_blueprint(routes.event_assignment_bp)
    monkeypatch.setattr(routes, "create_authenticated_supabase_client", lambda token: fake_client)
    return app.test_client()


def test_assigned_events_requires_login(client):
    response = client.get("/api/event-assignment/assigned-events")

    assert response.status_code == 401


def test_assigned_events_returns_coordinator_events(client, monkeypatch):
    monkeypatch.setattr(service, "get_current_user_id", lambda c, t: COORDINATOR_ID)

    response = client.get(
        "/api/event-assignment/assigned-events",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert [e["name"] for e in response.get_json()["events"]] == ["Northstar Industry Forum"]


def test_event_assignment_rejects_invalid_event_id(client, monkeypatch):
    monkeypatch.setattr(service, "get_current_user_id", lambda c, t: ORGANISER_ID)

    response = client.get(
        "/api/event-assignment/events/not-a-uuid",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 404