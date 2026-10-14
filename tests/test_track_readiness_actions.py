from datetime import date
from types import SimpleNamespace

import pytest
from flask import Flask

from app.routes import track_readiness_actions_routes as routes
from app.services import track_readiness_actions_service as service

TODAY = date(2026, 9, 30)


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
        update = next((a[0] for n, a, _ in self._log if n == "update"), None)
        if update is not None:  # an update returns the matched rows with the new values
            return SimpleNamespace(data=[{**row, **update} for row in self._data])
        return SimpleNamespace(data=self._data)


class FakeClient:
    def __init__(self, tables):
        self.tables = tables
        self.log = []

    def table(self, name):
        self.log.append(("table", (name,), {}))
        # each query gets its own log so an "update" never leaks into a later select
        query_log = []
        self.log.append(("query", (name,), {"log": query_log}))
        return FakeQuery(self.tables.get(name, []), query_log)

    def updates(self):
        return [a[0] for n, _, kw in self.log if n == "query" for m, a, _ in kw["log"] if m == "update"]


def make_client(*, event_status="planning", technical_requirements=None, bookings=(), reservations=(),
                equipment=(("eq1", "Projector"), ("eq2", "Microphone")), coordinator=True, assigned=True):
    event = [{
        "event_id": "e1", "name": "Northstar Industry Forum", "status": event_status,
        "coordinator_id": "c1", "technical_requirements": technical_requirements,
    }] if assigned else []
    return FakeClient({
        "user_role": [{"user_id": "c1", "role": "event_coordinator"}] if coordinator else [],
        "event": event,
        "venue_booking": list(bookings),
        "equipment_reservation": list(reservations),
        "equipment": [{"equipment_id": i, "name": n} for i, n in equipment],
    })


def booking(status):
    return {"booking_id": "b1", "event_id": "e1", "status": status}


def reservation(equipment_id, status):
    return {"reservation_id": f"r-{equipment_id}", "event_id": "e1", "equipment_id": equipment_id,
            "status": status, "quantity_requested": 1}


@pytest.fixture
def no_extra_sources(monkeypatch):
    monkeypatch.setattr(service, "_load_programme_status", lambda c, e: "completed")
    monkeypatch.setattr(service, "_load_tasks", lambda c, e: [])


# TC-001
def test_incomplete_readiness_lists_outstanding_actions_and_overdue_tasks(monkeypatch):
    monkeypatch.setattr(service, "_load_programme_status", lambda c, e: "in_progress")
    monkeypatch.setattr(service, "_load_tasks", lambda c, e: [
        {"name": "Confirm speaker schedule", "responsible": "Jordan Lee", "deadline": "2026-09-28", "status": "in_progress"},
        {"name": "Prepare attendee materials", "responsible": "Mina Patel", "deadline": "2026-10-05", "status": "not_started"},
    ])
    client = make_client(bookings=[booking("requested")], reservations=[reservation("eq1", "requested")])

    result = service.get_readiness(client, "c1", "e1", today=TODAY)

    assert result["readiness"] == "Incomplete"
    assert result["can_confirm"] is False
    kinds = [a["type"] for a in result["outstanding_actions"]]
    assert {"venue", "equipment", "programme"} <= set(kinds) and kinds.count("task") == 2
    tasks = {t["name"]: t for t in result["unfinished_tasks"]}
    assert tasks["Confirm speaker schedule"]["overdue"] is True
    assert tasks["Confirm speaker schedule"]["responsible"] == "Jordan Lee"
    assert tasks["Prepare attendee materials"]["overdue"] is False
    assert result["equipment_reservations"][0]["equipment_name"] == "Projector"


# TC-002
def test_ready_when_all_conditions_met_including_no_equipment_and_no_tasks(no_extra_sources):
    client = make_client(bookings=[booking("confirmed")], technical_requirements="No equipment required")
    result = service.get_readiness(client, "c1", "e1", today=TODAY)
    assert result["readiness"] == "Ready for Confirmation"
    assert result["can_confirm"] is True
    assert result["outstanding_actions"] == []
    assert result["conditions"]["tasks"]["detail"] == "No tasks exist."


def test_no_equipment_phrase_is_case_and_punctuation_tolerant(no_extra_sources):
    client = make_client(bookings=[booking("confirmed")], technical_requirements="  no equipment required. ")
    assert service.get_readiness(client, "c1", "e1", today=TODAY)["conditions"]["equipment"]["complete"]


def test_equipment_incomplete_when_nothing_reserved_and_no_explicit_choice(no_extra_sources):
    client = make_client(bookings=[booking("confirmed")], technical_requirements="Projector and microphones")
    result = service.get_readiness(client, "c1", "e1", today=TODAY)
    assert result["readiness"] == "Incomplete"
    assert result["conditions"]["equipment"]["complete"] is False


# TC-003
def test_confirmation_blocked_when_equipment_reservation_not_confirmed(no_extra_sources):
    client = make_client(bookings=[booking("confirmed")], reservations=[reservation("eq1", "requested")])
    with pytest.raises(service.ReadinessError) as exc:
        service.confirm_event(client, "c1", "e1", today=TODAY)
    assert exc.value.status_code == 409
    assert exc.value.readiness["readiness"] == "Incomplete"
    assert exc.value.readiness["outstanding_actions"][0]["type"] == "equipment"
    assert client.updates() == []  # existing status retained


# TC-004
def test_confirm_updates_status_to_confirmed(no_extra_sources):
    client = make_client(bookings=[booking("confirmed")], reservations=[reservation("eq1", "reserved")])
    event = service.confirm_event(client, "c1", "e1", today=TODAY)
    assert event["status"] == "confirmed"
    assert client.updates()[0]["status"] == "confirmed"
    assert client.updates()[0]["updated_at"]


# TC-005
def test_venue_and_equipment_need_confirmed_status_then_refresh(no_extra_sources):
    before = make_client(
        bookings=[booking("tentative")],
        reservations=[reservation("eq1", "requested"), reservation("eq2", "reserved")],
    )
    result = service.get_readiness(before, "c1", "e1", today=TODAY)
    assert result["readiness"] == "Incomplete"
    assert [a["type"] for a in result["outstanding_actions"]] == ["venue", "equipment"]
    assert "Projector" in result["outstanding_actions"][1]["message"]

    after = make_client(
        bookings=[booking("confirmed")],
        reservations=[reservation("eq1", "reserved"), reservation("eq2", "reserved")],
    )
    assert service.get_readiness(after, "c1", "e1", today=TODAY)["readiness"] == "Ready for Confirmation"


def test_cancelled_reservation_and_rejected_booking_are_ignored(no_extra_sources):
    client = make_client(
        bookings=[booking("rejected"), booking("confirmed")],
        reservations=[reservation("eq1", "reserved"), reservation("eq2", "cancelled")],
    )
    assert service.get_readiness(client, "c1", "e1", today=TODAY)["readiness"] == "Ready for Confirmation"


def test_rejected_reservation_still_blocks(no_extra_sources):
    client = make_client(bookings=[booking("confirmed")], reservations=[reservation("eq1", "rejected")])
    assert service.get_readiness(client, "c1", "e1", today=TODAY)["conditions"]["equipment"]["complete"] is False


def test_only_rejected_or_no_booking_means_venue_outstanding(no_extra_sources):
    client = make_client(bookings=[booking("rejected")], technical_requirements="No equipment required")
    result = service.get_readiness(client, "c1", "e1", today=TODAY)
    assert result["conditions"]["venue"]["complete"] is False


def test_programme_and_tasks_untracked_in_current_schema():
    client = make_client(bookings=[booking("confirmed")], technical_requirements="No equipment required")
    result = service.get_readiness(client, "c1", "e1", today=TODAY)
    assert result["conditions"]["programme"]["tracked"] is False
    assert result["readiness"] == "Ready for Confirmation"


def test_completed_tasks_do_not_block(monkeypatch, no_extra_sources):
    monkeypatch.setattr(service, "_load_tasks", lambda c, e: [
        {"name": "Confirm speaker schedule", "responsible": "Jordan Lee", "deadline": "2026-09-28", "status": "Completed"}])
    client = make_client(bookings=[booking("confirmed")], technical_requirements="No equipment required")
    assert service.get_readiness(client, "c1", "e1", today=TODAY)["readiness"] == "Ready for Confirmation"


def test_confirmation_only_allowed_from_planning_status(no_extra_sources):
    client = make_client(event_status="requested", bookings=[booking("confirmed")],
                         technical_requirements="No equipment required")
    with pytest.raises(service.ReadinessError) as exc:
        service.confirm_event(client, "c1", "e1", today=TODAY)
    assert exc.value.status_code == 409
    assert client.updates() == []


def test_event_not_assigned_to_coordinator_is_not_found():
    with pytest.raises(service.ReadinessError) as exc:
        service.get_readiness(make_client(assigned=False), "c1", "e1", today=TODAY)
    assert exc.value.status_code == 404


def test_non_coordinator_is_rejected():
    with pytest.raises(service.ReadinessError) as exc:
        service.get_readiness(make_client(coordinator=False), "c1", "e1", today=TODAY)
    assert exc.value.status_code == 403


def test_list_assigned_events():
    events = service.list_assigned_events(make_client(), "c1")
    assert events[0]["name"] == "Northstar Industry Forum"


# Route-level checks
@pytest.fixture
def http(monkeypatch, no_extra_sources):
    app = Flask(__name__)
    app.register_blueprint(routes.track_readiness_actions_bp)

    def use(client):
        monkeypatch.setattr(routes, "_authenticate", lambda: (client, "c1"))
        return app.test_client()
    return use


def test_readiness_route_returns_readiness(http):
    res = http(make_client(bookings=[booking("requested")])).get("/api/track-readiness-actions/events/e1")
    assert res.status_code == 200
    assert res.get_json()["readiness"] == "Incomplete"


def test_confirm_route_returns_409_with_outstanding_actions(http):
    res = http(make_client(bookings=[booking("requested")])).post("/api/track-readiness-actions/events/e1/confirm")
    assert res.status_code == 409
    assert res.get_json()["readiness"]["outstanding_actions"]


def test_confirm_route_success(http):
    client = make_client(bookings=[booking("confirmed")], technical_requirements="No equipment required")
    res = http(client).post("/api/track-readiness-actions/events/e1/confirm")
    assert res.status_code == 200
    assert res.get_json()["event"]["status"] == "confirmed"


def test_routes_require_authentication():
    app = Flask(__name__)
    app.register_blueprint(routes.track_readiness_actions_bp)
    assert app.test_client().get("/api/track-readiness-actions/events").status_code == 401