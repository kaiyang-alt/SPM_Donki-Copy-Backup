"""Automated tests for docs/test-cases/add-new-equipment.md (TC-001 to TC-008)."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from app.app import app
from app.services import add_new_equipment_service as service
from app.services.equipment_reservation_service import EquipmentError

VALID = {"name": "Wireless Lapel Microphone", "type": "Audio",
         "description": "Clip-on wireless microphone with receiver",
         "location": "Main Store, Level 1", "total_quantity": 8}


class FakeTable:
    """Minimal query builder that applies eq/in_ filters, so role checks are really tested."""

    def __init__(self, store, name):
        self.store, self.name, self.filters, self.payload = store, name, [], None

    def select(self, *_):
        return self

    def eq(self, column, value):
        self.filters.append(lambda row: row.get(column) == value)
        return self

    def in_(self, column, values):
        self.filters.append(lambda row: row.get(column) in values)
        return self

    def limit(self, *_):
        return self

    def order(self, *_):
        return self

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        rows = self.store["tables"][self.name]
        if self.payload is not None:
            if self.store["insert_error"]:
                raise self.store["insert_error"]
            self.store["inserts"].append(deepcopy(self.payload))
            saved = {"equipment_id": f"eq-{len(rows) + 1}", **self.payload}
            rows.append(saved)
            return SimpleNamespace(data=[deepcopy(saved)])
        return SimpleNamespace(data=[deepcopy(r) for r in rows if all(f(r) for f in self.filters)])


@pytest.fixture
def database():
    store = {"inserts": [], "insert_error": None, "tables": {
        "user_role": [{"user_id": "tss", "role": "technical_support"},
                      {"user_id": "coordinator", "role": "event_coordinator"}],
        "equipment": [{"equipment_id": "eq-1", "name": "Wireless Lapel Microphone", "type": "Audio",
                       "description": "Original batch", "location": "Main Store, Level 1",
                       "total_quantity": 6, "active": True},
                      {"equipment_id": "eq-2", "name": "Retired Projector", "type": "Visual",
                       "description": "Written off", "location": "Main Store", "total_quantity": 1,
                       "active": False}],
    }}
    client = MagicMock()
    client.table.side_effect = lambda name: FakeTable(store, name)
    return client, store


def names(result):
    return [item["name"] for item in result["equipment"]]


# TC-001 / AC1, AC5
def test_valid_equipment_is_saved_active_and_listed_immediately(database):
    client, store = database
    padded = {key: f"  {value}  " if isinstance(value, str) else value for key, value in VALID.items()}
    saved = service.add_equipment(client, "tss", {**padded, "name": "  Portable PA Speaker  "})["equipment"]
    assert store["inserts"] == [{**VALID, "name": "Portable PA Speaker", "active": True}]
    assert saved["equipment_id"] and saved["active"] is True
    assert "Portable PA Speaker" in names(service.list_catalogue(client, "tss"))


# TC-001 / AC1: the client cannot choose the ID or save an inactive item.
def test_client_supplied_id_and_active_flag_are_ignored(database):
    client, store = database
    service.add_equipment(client, "tss", {**VALID, "equipment_id": "chosen", "active": False})
    assert store["inserts"][0]["active"] is True
    assert "equipment_id" not in store["inserts"][0]


# TC-002 / AC2
@pytest.mark.parametrize("quantity", [1, "1"])
def test_minimum_quantity_of_one_is_accepted(database, quantity):
    client, store = database
    service.add_equipment(client, "tss", {**VALID, "total_quantity": quantity})
    assert store["inserts"][0]["total_quantity"] == 1


# TC-003 / AC3
@pytest.mark.parametrize("field,label", [("name", "Name"), ("type", "Category"), ("description", "Description"),
                                         ("location", "Location"), ("total_quantity", "Total quantity")])
@pytest.mark.parametrize("missing", ["absent", None, ""])
def test_omitted_mandatory_field_blocks_saving(database, field, label, missing):
    client, store = database
    payload = {**VALID}
    if missing == "absent":
        del payload[field]
    else:
        payload[field] = missing
    with pytest.raises(EquipmentError, match=f"{label} is required") as exc:
        service.add_equipment(client, "tss", payload)
    assert exc.value.status_code == 400
    assert store["inserts"] == []


# TC-004 / AC3
@pytest.mark.parametrize("field,label", [("name", "Name"), ("type", "Category"), ("description", "Description"),
                                         ("location", "Location"), ("total_quantity", "Total quantity")])
def test_whitespace_only_field_is_treated_as_omitted(database, field, label):
    client, store = database
    with pytest.raises(EquipmentError, match=f"{label} is required"):
        service.add_equipment(client, "tss", {**VALID, field: "   "})
    assert store["inserts"] == []


# TC-005 / AC2, AC4
@pytest.mark.parametrize("quantity", [0, -1, 2.5, "0", "-1", "2.5", "abc", True, [3]])
def test_invalid_quantity_blocks_saving(database, quantity):
    client, store = database
    with pytest.raises(EquipmentError, match="whole number greater than 0") as exc:
        service.add_equipment(client, "tss", {**VALID, "total_quantity": quantity})
    assert exc.value.status_code == 400
    assert store["inserts"] == []


# TC-003 / TC-005: all problems are reported together.
def test_every_validation_problem_is_reported(database):
    client, _ = database
    with pytest.raises(EquipmentError) as exc:
        service.add_equipment(client, "tss", {"total_quantity": 0})
    message = str(exc.value)
    for expected in ["Name is required", "Category is required", "Description is required",
                     "Location is required", "whole number greater than 0"]:
        assert expected in message


# TC-006 / AC5
def test_coordinator_sees_new_equipment_but_not_inactive_items(database):
    client, _ = database
    service.add_equipment(client, "tss", {**VALID, "name": "4K Laser Projector"})
    listed = names(service.list_catalogue(client, "coordinator"))
    assert "4K Laser Projector" in listed
    assert "Retired Projector" not in listed


# TC-007 / AC7
def test_duplicate_name_is_saved_as_a_separate_item(database):
    client, store = database
    service.add_equipment(client, "tss", {**VALID, "description": "Second batch purchased for East Wing",
                                          "location": "East Wing Store", "total_quantity": 4})
    matches = [r for r in store["tables"]["equipment"] if r["name"] == "Wireless Lapel Microphone"]
    assert [(r["location"], r["total_quantity"]) for r in matches] == [
        ("Main Store, Level 1", 6), ("East Wing Store", 4)]


# TC-008 / AC6
@pytest.mark.parametrize("role", ["event_coordinator", "event_organiser", "venue_staff", "attendee"])
def test_non_technical_roles_cannot_add_equipment(database, role):
    client, store = database
    store["tables"]["user_role"] = [{"user_id": "someone", "role": role}]
    with pytest.raises(EquipmentError, match="Technical Support access") as exc:
        service.add_equipment(client, "someone", VALID)
    assert exc.value.status_code == 403
    assert store["inserts"] == []


# TC-008 / AC6: the role check runs before validation, so unauthorised users learn nothing about the rules.
def test_role_is_checked_before_validation(database):
    client, store = database
    store["tables"]["user_role"] = []
    with pytest.raises(EquipmentError) as exc:
        service.add_equipment(client, "someone", {})
    assert exc.value.status_code == 403


@pytest.mark.parametrize("role", ["event_organiser", "venue_staff", "attendee"])
def test_other_roles_cannot_read_the_catalogue(database, role):
    client, store = database
    store["tables"]["user_role"] = [{"user_id": "someone", "role": role}]
    with pytest.raises(EquipmentError) as exc:
        service.list_catalogue(client, "someone")
    assert exc.value.status_code == 403


# AC6 at the database layer: an RLS denial is reported as a permission error.
def test_rls_denial_is_reported_as_forbidden(database):
    client, store = database
    store["insert_error"] = APIError({"code": "42501", "message": "new row violates row-level security policy"})
    with pytest.raises(EquipmentError) as exc:
        service.add_equipment(client, "tss", VALID)
    assert exc.value.status_code == 403
    assert "row-level" not in str(exc.value)


def test_unknown_database_error_is_sanitised(database):
    client, store = database
    store["insert_error"] = APIError({"code": "XX000", "message": "secret internal SQL"})
    with pytest.raises(EquipmentError) as exc:
        service.add_equipment(client, "tss", VALID)
    assert exc.value.status_code == 503
    assert "secret" not in str(exc.value)


@pytest.fixture
def route_client(monkeypatch, database):
    client = database[0]
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id="tss"))
    # _handle is reused from the equipment reservation routes, so patch the client there.
    monkeypatch.setattr("app.routes.equipment_reservations.create_authenticated_supabase_client", lambda token: client)
    return app.test_client()


# TC-001, TC-008: route registration, authentication and the form's string quantity.
def test_route_adds_equipment_and_returns_saved_row(route_client, database):
    _, store = database
    assert route_client.post("/api/equipment-catalogue", json=VALID).status_code == 401
    response = route_client.post("/api/equipment-catalogue", headers={"Authorization": "Bearer token"},
                                 json={**VALID, "total_quantity": "8"})
    assert response.status_code == 200
    assert response.json["equipment"]["total_quantity"] == 8
    assert len(store["inserts"]) == 1


def test_route_returns_validation_error_without_saving(route_client, database):
    _, store = database
    response = route_client.post("/api/equipment-catalogue", headers={"Authorization": "Bearer token"},
                                 json={**VALID, "total_quantity": 0})
    assert response.status_code == 400
    assert "whole number greater than 0" in response.json["error"]
    assert store["inserts"] == []


def test_route_lists_active_catalogue(route_client):
    assert route_client.get("/api/equipment-catalogue").status_code == 401
    response = route_client.get("/api/equipment-catalogue", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert [item["name"] for item in response.json["equipment"]] == ["Wireless Lapel Microphone"]