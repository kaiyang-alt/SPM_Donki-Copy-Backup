from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from app.app import app
from app.services import equipment_reservation_service as service
from app.services.auth_service import login_user


REQUEST_ID = "12345678-1234-1234-1234-123456789012"


@pytest.fixture
def database():
    client = MagicMock()
    row = {"reservation_id": REQUEST_ID, "event_id": "event-1", "equipment_id": "eq-1",
           "quantity_requested": 1, "start_datetime": "2026-11-20T09:00:00+08:00",
           "end_datetime": "2026-11-20T12:00:00+08:00", "status": "requested",
           "requested_at": "2026-11-19T08:00:00+08:00", "requested_by": "tss",
           "quantity_suggested": 1, "proposal_version": 1, "organiser_agreed_version": 1,
           "organiser_agreed_by": "owner", "organiser_agreed_at": "2026-11-19T09:00:00Z"}
    data = {"user_role": [{"role": "technical_support"}], "equipment_reservation": [row],
            "event": [{"event_id": "event-1", "name": "Northstar", "status": "approved", "organiser_id": "owner"}],
            "equipment": [{"equipment_id": "eq-1", "name": "Projector", "type": "Projector", "total_quantity": 1}]}
    queries = {}
    for table in data:
        query = MagicMock()
        for method in ["select", "eq", "limit", "in_", "order", "or_"]:
            getattr(query, method).return_value = query
        query.execute.side_effect = lambda name=table: SimpleNamespace(data=deepcopy(data[name]))
        queries[table] = query
    client.table.side_effect = lambda name: queries[name]
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="tss"))
    return client, data, queries


def test_list_reads_existing_requests_and_related_metadata(database):
    client, data, queries = database
    result = service.list_requests(client, "tss")
    assert result[0]["reservation"] == data["equipment_reservation"][0]
    assert result[0]["equipment"]["type"] == "Projector"
    queries["equipment_reservation"].in_.assert_called_once_with("status", ["requested", "reserved"])
    queries["equipment_reservation"].order.assert_called_once_with("requested_at")


@pytest.mark.parametrize("event_status", ["approved", "confirmed"])
@pytest.mark.parametrize("free,sufficient", [(0, False), (1, True), (2, True), (-1, False)])
def test_availability_uses_approved_timeline_helper(database, free, sufficient, event_status):
    client, data, queries = database
    data["event"][0]["status"] = event_status
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=free)
    result = service.availability(client, "tss", REQUEST_ID)
    assert result["sufficient_stock"] is sufficient
    assert result["available_quantity"] == max(0, free)
    client.rpc.assert_called_once_with("cs_equipment_request_available", {"p_reservation_id": REQUEST_ID})
    assert data["equipment_reservation"][0]["status"] == "requested"
    queries["equipment_reservation"].update.assert_not_called()


@pytest.mark.parametrize("as_list", [False, True])
def test_acceptance_preserves_request_and_confirms_rpc_returned_row(database, as_list):
    client, data, queries = database
    saved = {**data["equipment_reservation"][0], "status": "reserved",
             "decided_by": "tss", "decided_at": "2026-11-19T09:00:00Z"}
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=[saved] if as_list else saved)
    result = service.accept_request(client, "tss", REQUEST_ID)
    client.rpc.assert_called_once_with("accept_equipment_request", {"p_reservation_id": REQUEST_ID})
    assert result["reservation"] == saved
    assert result["event"]["name"] == "Northstar"
    assert result["equipment"]["name"] == "Projector"
    for query in queries.values():
        query.update.assert_not_called()
        query.insert.assert_not_called()
    assert data["event"][0]["status"] == "approved"


def test_retry_of_reserved_request_still_uses_idempotent_rpc(database):
    client, data, _ = database
    data["equipment_reservation"][0]["status"] = "reserved"
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=data["equipment_reservation"][0])
    assert service.accept_request(client, "tss", REQUEST_ID)["reservation"]["status"] == "reserved"
    client.rpc.assert_called_once()


@pytest.mark.parametrize("message", [
    "Equipment commitments contain invalid or ambiguous data",
    "Equipment unavailable, or stock is required for an earlier request",
    "Equal or missing request timestamps need a confirmed priority decision",
])
def test_rpc_ambiguity_and_stock_conflicts_keep_pending_request(database, message):
    client, data, queries = database
    client.rpc.return_value.execute.side_effect = APIError({"code": "P0001", "message": message, "details": None, "hint": None})
    with pytest.raises(service.EquipmentError) as exc:
        service.accept_request(client, "tss", REQUEST_ID)
    assert exc.value.status_code == 409
    assert data["equipment_reservation"][0]["status"] == "requested"
    queries["equipment_reservation"].update.assert_not_called()


def test_null_unavailability_error_is_not_displayed_as_zero_or_available(database):
    client, _, _ = database
    client.rpc.return_value.execute.side_effect = APIError({"code": "P0001", "message": "Equipment commitments contain invalid or ambiguous data"})
    with pytest.raises(service.EquipmentError, match="ambiguous"):
        service.availability(client, "tss", REQUEST_ID)


@pytest.mark.parametrize("code", ["PGRST202", "PGRST204", "42883", "42703"])
def test_missing_database_setup_is_reported_without_fallback_update(database, code):
    client, _, queries = database
    client.rpc.return_value.execute.side_effect = APIError({"code": code, "message": "private internal detail"})
    with pytest.raises(service.EquipmentError, match="not configured") as exc:
        service.accept_request(client, "tss", REQUEST_ID)
    assert exc.value.status_code == 503
    queries["equipment_reservation"].update.assert_not_called()


def test_unknown_database_error_is_sanitised(database):
    client, _, _ = database
    client.rpc.return_value.execute.side_effect = APIError({"code": "XX000", "message": "secret internal SQL"})
    with pytest.raises(service.EquipmentError) as exc:
        service.accept_request(client, "tss", REQUEST_ID)
    assert "secret" not in str(exc.value)


def test_hidden_related_event_prevents_acceptance_before_commit(database):
    client, data, _ = database
    data["event"] = []
    with pytest.raises(service.EquipmentError) as exc:
        service.accept_request(client, "tss", REQUEST_ID)
    assert exc.value.status_code == 403
    client.rpc.assert_not_called()


def test_ineligible_event_cannot_pass_availability(database):
    client, data, _ = database
    data["event"][0]["status"] = "cancelled"
    with pytest.raises(service.EquipmentError):
        service.availability(client, "tss", REQUEST_ID)
    client.rpc.assert_not_called()


@pytest.mark.parametrize("request_status", ["planning", "reserved", "rejected", "cancelled"])
def test_only_requested_equipment_can_pass_availability(database, request_status):
    client, data, _ = database
    data["equipment_reservation"][0]["status"] = request_status
    with pytest.raises(service.EquipmentError, match="Only requested equipment requests") as exc:
        service.availability(client, "tss", REQUEST_ID)
    assert exc.value.status_code == 409
    client.rpc.assert_not_called()


def test_rpc_wrong_request_status_returns_conflict(database):
    client, _, _ = database
    client.rpc.return_value.execute.side_effect = APIError({
        "code": "P0001", "message": "Only requested equipment requests can be accepted",
    })
    with pytest.raises(service.EquipmentError, match="Only requested equipment requests") as exc:
        service.accept_request(client, "tss", REQUEST_ID)
    assert exc.value.status_code == 409


@pytest.fixture
def route_client(monkeypatch, database):
    monkeypatch.setattr("app.routes.equipment_reservations.create_authenticated_supabase_client", lambda token: database[0])
    return app.test_client()


def test_real_app_registers_authenticated_equipment_routes(route_client, database):
    assert route_client.get("/api/equipment-requests").status_code == 401
    response = route_client.get("/api/equipment-requests", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.json["requests"][0]["reservation"]["reservation_id"] == REQUEST_ID


def test_detail_route_returns_fresh_event_requirements_and_booking_details(route_client, database):
    _, data, _ = database
    data["event"][0].update({
        "description": "Real event details", "technical_requirements": "One projector",
        "venue_booking": [{"booking_id": "booking-1", "venue_id": "venue-1",
                           "status": "confirmed", "venue": {"name": "Seminar Room"}}],
    })
    assert route_client.get(f"/api/equipment-requests/{REQUEST_ID}").status_code == 401
    response = route_client.get(f"/api/equipment-requests/{REQUEST_ID}", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.json["event"]["technical_requirements"] == "One projector"
    assert response.json["event"]["venue_booking"][0]["venue"]["name"] == "Seminar Room"


def test_detail_route_does_not_invent_or_hide_inaccessible_requests(route_client, database):
    _, data, _ = database
    data["equipment_reservation"] = []
    response = route_client.get(f"/api/equipment-requests/{REQUEST_ID}", headers={"Authorization": "Bearer token"})
    assert response.status_code == 404


def test_detail_route_respects_event_rls(route_client, database):
    _, data, _ = database
    data["event"] = []
    response = route_client.get(f"/api/equipment-requests/{REQUEST_ID}", headers={"Authorization": "Bearer token"})
    assert response.status_code == 403


@pytest.mark.parametrize("path,method", [("", "get"), (f"/{REQUEST_ID}", "get"), (f"/{REQUEST_ID}/accept", "post"), (f"/{REQUEST_ID}/availability", "get")])
def test_non_technical_role_cannot_read_or_accept(route_client, database, path, method):
    client, data, _ = database
    data["user_role"] = []
    response = getattr(route_client, method)("/api/equipment-requests" + path, headers={"Authorization": "Bearer token"})
    assert response.status_code == 403
    client.rpc.assert_not_called()


def test_route_ignores_client_supplied_reservation_changes(route_client, database):
    client, data, _ = database
    saved = {**data["equipment_reservation"][0], "status": "reserved"}
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=saved)
    response = route_client.post(f"/api/equipment-requests/{REQUEST_ID}/accept",
        headers={"Authorization": "Bearer token"}, json={"quantity_requested": 999, "event_id": "other", "status": "reserved"})
    assert response.status_code == 200
    assert response.json["reservation"] == saved
    client.rpc.assert_called_once_with("accept_equipment_request", {"p_reservation_id": REQUEST_ID})


def test_invalid_request_id_never_calls_rpc(route_client, database):
    response = route_client.post("/api/equipment-requests/invalid/accept", headers={"Authorization": "Bearer token"})
    assert response.status_code == 400
    database[0].rpc.assert_not_called()


def test_technical_support_can_use_existing_application_login(monkeypatch):
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id="tss", email="tss@example.test"),
        session=SimpleNamespace(access_token="token", refresh_token="refresh"))
    profile, roles = MagicMock(), MagicMock()
    profile.select.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(data=[{"user_id": "tss"}])
    roles.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(data=[{"role": "technical_support"}])
    client.table.side_effect = lambda name: {"profile": profile, "user_role": roles}[name]
    monkeypatch.setattr("app.services.auth_service.create_supabase_client", lambda: client)
    assert login_user("tss@example.test", "test-password")["roles"] == ["technical_support"]


def test_inbox_includes_coordinator_approved_requirements_without_equipment_rows(database):
    client, data, queries = database
    data["equipment_reservation"] = []
    data["event"] = [{"event_id": "event-1", "name": "New organiser submission", "status": "approved",
                      "technical_support_required": False, "technical_requirements": "Two microphones"}]
    result = service.technical_context(client, "tss")
    assert result["events"][0]["name"] == "New organiser submission"
    queries["event"].in_.assert_called_once_with("status", ["approved", "confirmed"])
    queries["event"].or_.assert_called_once_with("technical_support_required.eq.true,technical_requirements.not.is.null")
    client.rpc.assert_not_called()


def test_inbox_does_not_treat_blank_requirements_as_an_equipment_request(database):
    client, data, _ = database
    data["event"] = [{"event_id": "event-1", "technical_support_required": False, "technical_requirements": "  "}]
    assert service.technical_context(client, "tss")["events"] == []


@pytest.mark.parametrize("quantity", [None, 0, -1, 1.5, True, "3"])
def test_proposals_require_a_positive_integer_quantity(database, quantity):
    client, _, _ = database
    with pytest.raises(service.EquipmentError, match="Suggested quantity"):
        service.propose_quantity(client, "tss", {"event_id": REQUEST_ID,"equipment_id": REQUEST_ID,
          "quantity_suggested": quantity,"start_datetime": "2026-11-20T09:00:00+08:00","end_datetime": "2026-11-20T12:00:00+08:00"})
    client.rpc.assert_not_called()


@pytest.mark.parametrize("code", ["PGRST202", "PGRST204", "42883", "42703"])
def test_proposal_save_reports_missing_database_setup(route_client, database, code):
    client, _, queries = database
    client.rpc.return_value.execute.side_effect = APIError({"code": code, "message": "private internal SQL detail"})
    response = route_client.post("/api/equipment-requests/proposals",
        headers={"Authorization": "Bearer token"}, json={
            "event_id": REQUEST_ID, "equipment_id": REQUEST_ID,
            "quantity_suggested": 3, "start_datetime": "2026-11-20T09:00:00+08:00",
            "end_datetime": "2026-11-20T12:00:00+08:00",
        })
    assert response.status_code == 503
    assert "not configured in the database" in response.json["error"]
    assert "private internal" not in response.json["error"]
    queries["equipment_reservation"].insert.assert_not_called()
    queries["equipment_reservation"].update.assert_not_called()


def test_acceptance_requires_current_organiser_agreement(database):
    client, data, _ = database
    data["equipment_reservation"][0]["organiser_agreed_version"] = None
    with pytest.raises(service.EquipmentError, match="organiser must agree"):
        service.accept_request(client, "tss", REQUEST_ID)
    client.rpc.assert_not_called()


def test_availability_uses_the_offered_quantity_not_the_original_requirement(database):
    client, data, _ = database
    data["equipment_reservation"][0].update(quantity_requested=5,quantity_suggested=3)
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=3)
    result = service.availability(client, "tss", REQUEST_ID)
    assert result["sufficient_stock"] is True
    assert result["reservation"]["quantity_requested"] == 5
    assert result["reservation"]["quantity_suggested"] == 3


def test_another_organiser_cannot_agree_to_an_offer(database):
    client, data, _ = database
    data["user_role"] = [{"role": "event_organiser"}]
    with pytest.raises(service.EquipmentError, match="Only this event"):
        service.agree_proposal(client, "other-owner", REQUEST_ID, {"proposal_version": 1})
    client.rpc.assert_not_called()


def test_organiser_agreement_sends_version_only_and_never_updates_quantity(database):
    client, data, queries = database
    data["user_role"] = [{"role": "event_organiser"}]
    saved = data["equipment_reservation"][0]
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=saved)
    result = service.agree_proposal(client, "owner", REQUEST_ID, {"proposal_version": 1,"quantity_suggested": 999})
    client.rpc.assert_called_once_with("agree_equipment_proposal", {"p_reservation_id": REQUEST_ID,"p_expected_version": 1})
    assert result["reservation"]["quantity_suggested"] == 1
    queries["equipment_reservation"].update.assert_not_called()


@pytest.mark.parametrize("status", ["draft", "requested", "planning", "changes_requested"])
def test_technical_inbox_waits_for_coordinator_review(database, status):
    client, data, _ = database
    data["event"][0].update(status=status, technical_support_required=True)
    assert service.technical_context(client, "tss")["events"] == []
    assert service.list_requests(client, "tss") == []
    with pytest.raises(service.EquipmentError, match="Coordinator approval"):
        service.get_request(client, "tss", REQUEST_ID)
    with pytest.raises(service.EquipmentError, match="Coordinator approval"):
        service.accept_request(client, "tss", REQUEST_ID)
    client.rpc.assert_not_called()


@pytest.mark.parametrize("other_pending", [False, True])
def test_tss_reservation_hands_off_to_existing_coordinator_readiness(database, other_pending):
    from app.services import track_readiness_actions_service as readiness

    client, data, queries = database
    data["event"][0].update(coordinator_id="coordinator", technical_requirements="Projector")
    data["equipment_reservation"][0].update(quantity_requested=5, quantity_suggested=3)
    data["venue_booking"] = [{"event_id": "event-1", "status": "confirmed"}]
    booking_query = MagicMock()
    booking_query.select.return_value = booking_query
    booking_query.eq.return_value = booking_query
    booking_query.execute.side_effect = lambda: SimpleNamespace(data=deepcopy(data["venue_booking"]))
    queries["venue_booking"] = booking_query
    if other_pending:
        data["equipment_reservation"].append({
            "reservation_id": "another-request", "event_id": "event-1",
            "equipment_id": "eq-1", "status": "requested", "quantity_requested": 1,
        })

    def reserve():
        data["equipment_reservation"][0].update(status="reserved", decided_by="tss")
        return SimpleNamespace(data=deepcopy(data["equipment_reservation"][0]))

    client.rpc.return_value.execute.side_effect = reserve
    saved = service.accept_request(client, "tss", REQUEST_ID)
    assert saved["reservation"]["status"] == "reserved"
    assert data["event"][0]["status"] == "approved"
    queries["event"].update.assert_not_called()

    data["user_role"] = [{"role": "event_coordinator"}]
    assigned = readiness.list_assigned_events(client, "coordinator")
    assert assigned[0]["event_id"] == saved["reservation"]["event_id"]
    result = readiness.get_readiness(client, "coordinator", "event-1")
    assert result["equipment_reservations"][0]["status"] == "reserved"
    assert result["can_confirm"] is (not other_pending)
    if other_pending:
        with pytest.raises(readiness.ReadinessError, match="outstanding actions"):
            readiness.confirm_event(client, "coordinator", "event-1")
        queries["event"].update.assert_not_called()
    else:
        update_query = queries["event"]
        update_query.update.return_value = update_query
        # Keep the initial event read in approved; only the final update returns confirmed.
        update_query.execute.side_effect = [
            SimpleNamespace(data=deepcopy(data["event"])),
            SimpleNamespace(data=[{**data["event"][0], "status": "confirmed"}]),
        ]
        assert readiness.confirm_event(client, "coordinator", "event-1")["status"] == "confirmed"
        assert queries["event"].update.call_args.args[0]["status"] == "confirmed"
