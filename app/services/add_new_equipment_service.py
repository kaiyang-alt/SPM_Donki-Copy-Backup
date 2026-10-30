"""Technical Support equipment catalogue entry (add-new-equipment story)."""

import re

from postgrest.exceptions import APIError

from app.services.equipment_reservation_service import EquipmentError, ensure_technical_support

CATALOGUE_FIELDS = "equipment_id,name,type,description,location,total_quantity,active"
# Category is stored in the existing equipment.type column.
TEXT_FIELDS = (("name", "Name"), ("type", "Category"), ("description", "Description"), ("location", "Location"))
CATALOGUE_ROLES = ["technical_support", "event_coordinator"]
QUANTITY_ERROR = "Total quantity must be a whole number greater than 0."


def _quantity(value):
    """Return (quantity, error). Accepts a JSON integer or a whole-number string from the form."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, "Total quantity is required."
    if isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
        value = int(value.strip())
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        return None, QUANTITY_ERROR
    return value, None


def validate_equipment(payload):
    """Build the row to insert from allowed fields only; report every problem at once."""
    if not isinstance(payload, dict):
        raise EquipmentError("Provide equipment details.")
    values, errors = {}, []
    for key, label in TEXT_FIELDS:
        value = payload.get(key)
        text = value.strip() if isinstance(value, str) else ""
        if not text:
            errors.append(f"{label} is required.")
        values[key] = text
    values["total_quantity"], quantity_error = _quantity(payload.get("total_quantity"))
    if quantity_error:
        errors.append(quantity_error)
    if errors:
        raise EquipmentError(" ".join(errors))
    return values


def add_equipment(client, user_id, payload):
    ensure_technical_support(client, user_id)
    row = {**validate_equipment(payload), "active": True}
    try:
        saved = client.table("equipment").insert(row).execute().data
    except APIError as exc:
        if exc.code == "42501":
            raise EquipmentError("Technical Support access is required.", 403) from None
        raise EquipmentError("Unable to save the equipment. Please try again.", 503) from None
    if not saved:
        raise EquipmentError("Unable to verify the saved equipment. Refresh the catalogue before retrying.", 503)
    return {"equipment": saved[0]}


def list_catalogue(client, user_id):
    roles = (client.table("user_role").select("role").eq("user_id", user_id)
             .in_("role", CATALOGUE_ROLES).limit(1).execute().data)
    if not roles:
        raise EquipmentError("Technical Support or Event Coordinator access is required.", 403)
    items = (client.table("equipment").select(CATALOGUE_FIELDS)
             .eq("active", True).order("name").execute().data or [])
    return {"equipment": items}