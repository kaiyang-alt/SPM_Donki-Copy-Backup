"""Technical Support review, using the approved invoker RPCs under caller RLS."""

from uuid import UUID

from postgrest.exceptions import APIError


class EquipmentError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


# Only known database messages may reach the browser. Never expose raw errors.
RPC_ERRORS = {
    "Equipment unavailable, or stock is required for an earlier request":
        ("Equipment is unavailable or required for an earlier request.", 409),
    "Equipment commitments contain invalid or ambiguous data":
        ("Equipment commitments contain invalid or ambiguous data. Ask Technical Support to clarify them.", 409),
    "Equal or missing request timestamps need a confirmed priority decision":
        ("Equal or missing request timestamps require clarification before acceptance.", 409),
    "Equipment request not found or inaccessible": ("Equipment request not found or inaccessible.", 404),
    "Only planning equipment requests can be accepted": ("Only planning equipment requests can be accepted.", 409),
    "Event is inaccessible or not eligible for equipment acceptance":
        ("Event is inaccessible or not eligible for equipment acceptance.", 409),
    "Cannot verify the event for an earlier equipment request":
        ("Cannot verify the event for an earlier equipment request.", 409),
    "Requested quantity and request timestamp must be populated":
        ("The request needs a valid quantity and submission timestamp.", 409),
    "An earlier request has an invalid quantity": ("An earlier request needs quantity clarification.", 409),
    "Equipment stock is missing, inaccessible, or invalid":
        ("Equipment stock is missing, inaccessible, or invalid.", 409),
    "Equipment period must have a start before its end": ("The request needs a valid start and end time.", 409),
    "Request cannot be updated under the current RLS policies":
        ("The request cannot be accepted with your current permissions.", 403),
    "Technical Support authentication is required": ("Technical Support access is required.", 403),
    "Equipment stock would be overallocated": ("Equipment is unavailable for the full requested period.", 409),
}


def validate_id(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise EquipmentError("A valid equipment request ID is required.") from None


def ensure_technical_support(client, user_id):
    roles = (client.table("user_role").select("role").eq("user_id", user_id)
             .eq("role", "technical_support").limit(1).execute().data)
    if not roles:
        raise EquipmentError("Technical Support access is required.", 403)


def _rpc(client, name, params):
    try:
        return client.rpc(name, params).execute().data
    except APIError as exc:
        if exc.code in {"PGRST202", "42883"}:
            raise EquipmentError("Equipment acceptance is not configured. Contact the project team.", 503) from None
        if exc.message in RPC_ERRORS:
            message, status = RPC_ERRORS[exc.message]
            raise EquipmentError(message, status) from None
        if exc.code == "42501":
            raise EquipmentError("Equipment access is not permitted by your current permissions.", 403) from None
        raise EquipmentError("Unable to complete the equipment operation. Please try again.", 503) from None


def _related(client, reservation):
    event = (client.table("event").select("event_id,name,status")
             .eq("event_id", reservation["event_id"]).limit(1).execute().data)
    equipment = (client.table("equipment").select("equipment_id,name,type,total_quantity")
                 .eq("equipment_id", reservation["equipment_id"]).limit(1).execute().data)
    if not event or not equipment:
        raise EquipmentError("Required event or equipment information is not accessible.", 403)
    return {"reservation": reservation, "event": event[0], "equipment": equipment[0]}


def _request(client, reservation_id):
    rows = (client.table("equipment_reservation").select("*")
            .eq("reservation_id", validate_id(reservation_id)).limit(1).execute().data)
    if not rows:
        raise EquipmentError("Equipment request not found or inaccessible.", 404)
    return rows[0]


def list_requests(client, user_id):
    ensure_technical_support(client, user_id)
    rows = (client.table("equipment_reservation").select("*")
            .in_("status", ["planning", "reserved"]).order("requested_at").execute().data or [])
    # Do not silently hide a request whose related event is hidden by RLS.
    return [_related(client, row) for row in rows]


def availability(client, user_id, reservation_id):
    ensure_technical_support(client, user_id)
    row = _request(client, reservation_id)
    details = _related(client, row)
    if row.get("status") != "planning" or details["event"].get("status") not in {"planning", "confirmed"}:
        raise EquipmentError("Only planning requests for planning or confirmed events can be accepted.", 409)
    quantity = row.get("quantity_requested")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise EquipmentError("The request needs a valid required quantity.", 409)
    free = _rpc(client, "cs_equipment_free_quantity", {
        "p_equipment_id": row["equipment_id"],
        "p_start": row.get("start_datetime"), "p_end": row.get("end_datetime"),
    })
    if not isinstance(free, int) or isinstance(free, bool):
        raise EquipmentError("Unable to verify equipment availability.", 503)
    return {**details, "available_quantity": max(0, free), "sufficient_stock": free >= quantity}


def accept_request(client, user_id, reservation_id):
    ensure_technical_support(client, user_id)
    # Load presentation metadata before committing, so RLS gaps cannot turn a
    # saved reservation into a failed confirmation. The RPC decides acceptance.
    details = _related(client, _request(client, reservation_id))
    result = _rpc(client, "accept_equipment_request", {
        "p_reservation_id": validate_id(reservation_id),
    })
    # PostgREST versions may encode a returned composite as an object or list.
    if isinstance(result, list) and len(result) == 1:
        result = result[0]
    if not isinstance(result, dict) or result.get("reservation_id") != validate_id(reservation_id) or result.get("status") != "reserved":
        raise EquipmentError("Unable to verify acceptance. Reload the request before retrying.", 503)
    # Confirmation uses the actual RPC result, never an optimistic local row.
    return {**details, "reservation": result}
