"""B1 API contracts with a mocked RPC, never live authenticated invocation."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
from pathlib import Path
import shutil
import subprocess

import pytest

from app.app import app
from app.services.venue_occupancy import assess_schedule
from test_venue_booking import Database, HEADERS, active_booking


VENUE_A, VENUE_B = str(uuid4()), str(uuid4())
PAYLOAD = {"setup_minutes": 30, "turnaround_minutes": 45, "expected_revision": 0, "operation_id": str(uuid4())}


@pytest.fixture
def database():
    database = Database()
    database.auth.get_user.return_value.user.id = "STAFF-1"
    database.rows["venue"][0].update(venue_id=VENUE_A, setup_minutes=15, turnaround_minutes=15, buffer_config_revision=0)
    database.rows["venue"].append({**database.rows["venue"][0], "venue_id": VENUE_B})
    database.rpc = MagicMock()
    with patch("app.services.venue_booking_service.create_authenticated_supabase_client", return_value=database) as factory:
        database.factory = factory
        yield database


def save(payload=PAYLOAD, venue_id=VENUE_A):
    return app.test_client().put(f"/api/venues/{venue_id}/buffers", headers=HEADERS, json=payload)


def read(venue_id=VENUE_A):
    return app.test_client().get(f"/api/venues/{venue_id}/buffers", headers=HEADERS)


def outcome(**changes):
    return {"configuration_saved": True, "no_op": False, "configuration_revision": 1,
            "setup_minutes": 30, "turnaround_minutes": 45, "conflicts": [],
            "assessment_limitations": [], "assessment_complete": True,
            "authoritative_assessment_complete": True, "notification_status": "not_required",
            "routing_exceptions": [], **changes}


def test_independent_configuration_readback_and_caller_jwt_rpc(database):
    # Simulate only the trusted RPC's persistence; application writes are audited
    # separately below. This is not a test of deployed SQL transaction mechanics.
    def remote(name, params):
        assert name == "b1_save_venue_buffers"
        def execute():
            row = next(row for row in database.rows["venue"] if row["venue_id"] == params["p_venue_id"])
            row.update(setup_minutes=params["p_setup_minutes"], turnaround_minutes=params["p_turnaround_minutes"], buffer_config_revision=1)
            return SimpleNamespace(data=outcome(setup_minutes=row["setup_minutes"], turnaround_minutes=row["turnaround_minutes"]))
        return SimpleNamespace(execute=execute)
    database.rpc.side_effect = remote
    assert save().status_code == 200
    assert read().get_json()["setup_minutes"] == 30
    assert read(VENUE_B).get_json()["setup_minutes"] == 15
    assert save({**PAYLOAD, "setup_minutes": 45, "turnaround_minutes": 30, "operation_id": str(uuid4())}, VENUE_B).status_code == 200
    assert read(VENUE_B).get_json()["turnaround_minutes"] == 30
    assert read().get_json()["turnaround_minutes"] == 45
    database.factory.assert_called_with("test-token")
    database.rpc.assert_any_call("b1_save_venue_buffers", {
        "p_venue_id": VENUE_A, "p_setup_minutes": 30, "p_turnaround_minutes": 45,
        "p_expected_revision": 0, "p_operation_id": PAYLOAD["operation_id"],
    })
    assert not any(call[1] in ("update", "insert") for call in database.calls)


def test_unconfigured_nulls_remain_null(database):
    database.rows["venue"][0].update(setup_minutes=None, turnaround_minutes=None)
    result = read().get_json()
    assert result["configuration_state"] == "UNCONFIGURED"
    assert result["setup_minutes"] is None and result["turnaround_minutes"] is None
    assert result["buffer_config_revision"] == 0


@pytest.mark.parametrize("value,status,code", [(True, 400, "B1_INVALID_DURATION"), (1.5, 400, "B1_INVALID_DURATION"), ("30", 400, "B1_INVALID_DURATION"), ("3m", 400, "B1_INVALID_DURATION"), (-1, 400, "B1_INVALID_DURATION"), (None, 400, "B1_INVALID_INPUT"), (0, 409, "B1_ZERO_DECISION_REQUIRED")])
def test_input_validation_before_serialising(database, value, status, code):
    response = save({**PAYLOAD, "setup_minutes": value})
    assert response.status_code == status
    assert response.get_json()["code"] == code
    database.factory.assert_not_called()
    database.rpc.assert_not_called()


@pytest.mark.parametrize("change", [{"expected_revision": True}, {"expected_revision": "0"}, {"expected_revision": -1}, {"operation_id": "invalid"}, {"expected_revision": 2**63}, {"operation_id": None}])
def test_revision_and_token_validation(database, change):
    assert save({**PAYLOAD, **change}).status_code == 400
    database.factory.assert_not_called()


@pytest.mark.parametrize("field", ["operation_id", "expected_revision"])
def test_required_intent_fields(database, field):
    assert save({key: value for key, value in PAYLOAD.items() if key != field}).status_code == 400
    database.rpc.assert_not_called()


@pytest.mark.parametrize("field", ["event_id", "recipient_id", "message", "booking_id", "status"])
def test_caller_cannot_supply_derived_records_or_lifecycle(database, field):
    assert save({**PAYLOAD, field: "injected"}).status_code == 400
    database.rpc.assert_not_called()


def test_coordinator_cannot_edit_or_read_staff_configuration_api(database):
    database.auth.get_user.return_value.user.id = "COORD-ONLY"
    database.rows["user_role"].append({"user_id": "COORD-ONLY", "role": "event_coordinator"})
    assert save().status_code == 403
    assert read().status_code == 403
    database.rpc.assert_not_called()


def test_save_succeeds_with_conflicts_and_preserves_booking_event_data(database):
    database.rows["venue_booking"] = [
        active_booking(booking_id="A", venue_id=VENUE_A, status="confirmed", requested_start="2027-03-10T10:00:00+08:00", requested_end="2027-03-10T12:00:00+08:00"),
        active_booking(booking_id="B", venue_id=VENUE_A, status="confirmed", requested_start="2027-03-10T13:00:00+08:00", requested_end="2027-03-10T14:00:00+08:00"),
    ]
    before = deepcopy((database.rows["venue_booking"], database.rows["event"]))
    assessment = assess_schedule({"setup_minutes": 30, "turnaround_minutes": 45}, database.rows["venue_booking"], [])
    result = outcome(conflicts=assessment["conflicts"], notification_status="persisted", persisted_notices=[{"event_id": "A", "recipient_id": "Coordinator-A"}, {"event_id": "B", "recipient_id": "Coordinator-B"}])
    database.rpc.return_value.execute.return_value.data = result
    response = save()
    assert response.status_code == 200
    assert response.get_json()["conflicts"][0]["overlap_start"] == "2027-03-10T04:30:00+00:00"
    assert response.get_json()["persisted_notices"] == result["persisted_notices"]
    assert before == (database.rows["venue_booking"], database.rows["event"])


def test_routing_exception_is_distinct_from_full_notification_success(database):
    result = outcome(notification_status="incomplete_routing", routing_exceptions=[{"event_id": "A", "booking_ids": ["booking"], "reason": "missing_assigned_coordinator"}])
    database.rpc.return_value.execute.return_value.data = result
    response = save().get_json()
    assert response["configuration_saved"] is True
    assert response["notification_status"] == "incomplete_routing"
    assert response["routing_exceptions"] == result["routing_exceptions"]


def test_noop_and_b2_limitations_are_preserved(database):
    result = outcome(no_op=True, assessment_complete=False, assessment_limitations=[{"reason": "hold_validity_unavailable"}])
    database.rpc.return_value.execute.return_value.data = result
    assert save().get_json() == {"success": True, **result}


class Failure(Exception):
    def __init__(self, message, code="P0001"):
        super().__init__(message + " private SQL diagnostic")
        self.code = code


@pytest.mark.parametrize("message,db_code,status,public_code", [
    ("permission denied for function", "42501", 503, "B1_CAPABILITY_DISABLED"),
    ("missing function", "PGRST202", 503, "B1_CAPABILITY_DISABLED"),
    ("B1_STALE_CONFIGURATION_REVISION", "P0001", 409, "B1_STALE_CONFIGURATION_REVISION"),
    ("B1_AUTHORITATIVE_OCCUPANCY_UNASSESSABLE", "P0001", 409, "B1_AUTHORITATIVE_OCCUPANCY_UNASSESSABLE"),
    ("B1_OPERATION_TOKEN_REUSED", "P0001", 409, "B1_OPERATION_TOKEN_REUSED"),
    ("B1_ZERO_DECISION_REQUIRED", "P0001", 409, "B1_ZERO_DECISION_REQUIRED"),
    ("network lost", "", 503, "B1_SAVE_UNCONFIRMED"),
])
def test_database_failures_are_stable_and_do_not_leak_sql(database, message, db_code, status, public_code):
    database.rpc.return_value.execute.side_effect = Failure(message, db_code)
    response = save()
    assert response.status_code == status
    assert response.get_json()["code"] == public_code
    assert "SQL" not in response.get_json()["error"] and "private" not in response.get_json()["error"]


def test_buffer_routes_require_authentication():
    assert app.test_client().get(f"/api/venues/{VENUE_A}/buffers").status_code == 401
    assert app.test_client().put(f"/api/venues/{VENUE_A}/buffers", json=PAYLOAD).status_code == 401
    assert app.test_client().get("/api/venue-buffer-notifications").status_code == 401


def test_coordinator_inbox_uses_own_recipient_and_only_b1_notices(database):
    database.auth.get_user.return_value.user.id = "COORD-1"
    database.rows["notification"] = [
        {"notification_id": "own", "recipient_id": "COORD-1", "type": "venue_buffer_conflict", "message": "Review retained arrangement", "created_at": "2027-03-10T12:00:00Z"},
        {"notification_id": "other", "recipient_id": "COORD-2", "type": "venue_buffer_conflict"},
        {"notification_id": "different-story", "recipient_id": "COORD-1", "type": "assignment"},
    ]
    before = deepcopy(database.rows["notification"])
    response = app.test_client().get("/api/venue-buffer-notifications", headers=HEADERS)
    assert response.status_code == 200
    assert [row["notification_id"] for row in response.get_json()["notifications"]] == ["own"]
    assert database.rows["notification"] == before
    database.factory.assert_called_once_with("test-token")


def test_staff_only_cannot_read_coordinator_b1_inbox(database):
    assert app.test_client().get("/api/venue-buffer-notifications", headers=HEADERS).status_code == 403


def test_shared_supabase_factory_installs_caller_bearer_token():
    from app.supabase_client import create_authenticated_supabase_client
    with patch("app.supabase_client.create_client") as create_client:
        client = create_authenticated_supabase_client("caller-jwt")
        client.postgrest.auth.assert_called_once_with("caller-jwt")
        assert client is create_client.return_value


def test_existing_detail_endpoint_does_not_repurpose_buffer_writes(database):
    before = deepcopy(database.rows["venue"][0])
    response = app.test_client().put(f"/api/venues/{VENUE_A}", headers=HEADERS, json={
        "capacity": 120, "supported_layouts": ["Theatre"], "accessibility": "Step free",
        "setup_minutes": 999, "turnaround_minutes": 999, "buffer_config_revision": 999,
    })
    assert response.status_code == 200
    venue = database.rows["venue"][0]
    assert venue["capacity"] == 120
    assert venue["supported_layouts"] == ["Theatre"]
    assert venue["accessibility"] == "Step free"
    assert [venue[key] for key in ("setup_minutes", "turnaround_minutes", "buffer_config_revision")] == [before[key] for key in ("setup_minutes", "turnaround_minutes", "buffer_config_revision")]
    database.rpc.assert_not_called()


def test_schedule_retains_bookings_and_marks_changed_occupancy(database):
    database.rows["venue"][0].update(setup_minutes=30, turnaround_minutes=45)
    database.rows["venue_booking"] = [
        active_booking(booking_id="first", venue_id=VENUE_A, status="confirmed", requested_start="2027-03-10T10:00:00+08:00", requested_end="2027-03-10T12:00:00+08:00"),
        active_booking(booking_id="second", venue_id=VENUE_A, status="confirmed", requested_start="2027-03-10T13:00:00+08:00", requested_end="2027-03-10T14:00:00+08:00"),
    ]
    before = deepcopy(database.rows["venue_booking"])
    response = app.test_client().get(f"/api/venues/{VENUE_A}/schedule", headers=HEADERS)
    assert response.status_code == 200
    schedule = response.get_json()["schedule"]
    assert schedule["assessment_complete"] is True
    assert len(schedule["conflicts"]) == 1
    assert [row["booking_id"] for row in schedule["bookings_and_holds"]] == ["first", "second"]
    assert schedule["bookings_and_holds"][0]["occupied_start"] == "2027-03-10T01:30:00+00:00"
    assert database.rows["venue_booking"] == before


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is required for the B1 UI harness")
def test_ui_role_boundary_routing_render_and_retry_after_lost_response():
    script = r"""
const fs = require('fs'), vm = require('vm'), assert = require('assert');
let submit, calls = [], ids = 0, renders = 0;
const error = {textContent: ''}, button = {disabled: false};
const escape = value => String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const context = {
 roles: {venue: {nav: []}, coordinator: {nav: []}}, pages: {venue: {}, coordinator: {}},
 authSession: {access_token: 'caller'}, venueStaffVenues: [{venue_id: 'A', name: 'Hall', setup_minutes: null, turnaround_minutes: null, buffer_config_revision: 0}],
 selectedSchedule: {old: true}, availableVenues: ['old'], venueSearchResults: ['old'], venueSearchLimitations: [],
 pageHead: () => '', escapeHtml: escape, escapeAttribute: escape, formatDateTime: String,
 renderPage: () => renders++, crypto: {randomUUID: () => 'operation-' + (++ids)},
 document: {getElementById: id => id === 'mainContent' ? {addEventListener: (_, handler) => submit = handler} : error},
 authenticatedFetch: async (url, options) => {
   calls.push({url, payload: JSON.parse(options.body)});
   if (calls.length === 1) throw new Error('Lost response');
   return {ok: true, json: async () => ({configuration_saved: true, no_op: false, configuration_revision: 1, setup_minutes: 30, turnaround_minutes: 45, assessment_complete: true, conflicts: [], notification_status: 'persisted'})};
 }
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('app/static/js/venue-buffers.js', 'utf8'), context);
assert.strictEqual(context.pages.coordinator.venueBuffers, undefined);
assert(context.pages.coordinator.notifications().includes('Refresh venue notices'));
const html = context.pages.venue.venueBuffers();
assert(html.includes('Unconfigured'));
assert(html.includes('Revision: 0'));
assert(html.includes('value=""'));
const rendered = context.b1AssessmentDisplay({configuration_saved: true, configuration_revision: 2, assessment_complete: true, notification_status: 'incomplete_routing', conflicts: [{booking_id: '<script>', other_booking_id: 'B', overlap_start: '12:30', overlap_end: '12:45'}], routing_exceptions: [{reason: 'missing_assigned_coordinator'}]});
assert(rendered.includes('routing is incomplete'));
assert(rendered.includes('No assigned Coordinator could be found'));
const initial = context.b1AssessmentDisplay({configuration_saved: true, assessment_complete: true, assessment_limitations: [{reason: 'old_configuration_unconfigured'}]});
assert(initial.includes('Assessment notes') && !initial.includes('Assessment incomplete'));
assert(rendered.includes('&lt;script&gt;') && !rendered.includes('<script>'));
const form = {id: 'venueBuffersForm', elements: {setup: {value: '30'}, turnaround: {value: '45'}}, querySelector: () => button};
(async () => {
 await submit({target: form, preventDefault() {}});
 assert.strictEqual(error.textContent, 'Lost response');
 assert.strictEqual(context.venueStaffVenues[0].buffer_config_revision, 0);
 await submit({target: form, preventDefault() {}});
 assert.deepStrictEqual(calls[0], calls[1]);
 assert.strictEqual(ids, 1);
 assert.strictEqual(context.venueStaffVenues[0].buffer_config_revision, 1);
 assert.strictEqual(context.selectedSchedule, null);
 assert.strictEqual(context.availableVenues.length, 0);
 assert.strictEqual(context.venueSearchResults, null);
 assert.strictEqual(renders, 1);
 assert.strictEqual(button.disabled, false);
})().catch(error => {console.error(error); process.exitCode = 1;});
"""
    result = subprocess.run(["node", "-e", script], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
