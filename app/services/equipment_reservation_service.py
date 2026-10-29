"""Technical Support review, using the approved invoker RPCs under caller RLS."""

from uuid import UUID
from datetime import datetime

from postgrest.exceptions import APIError


class EquipmentError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


# Only known database messages may reach the browser. Never expose raw errors.
RPC_ERRORS = {
    "Venue commitments contain invalid or ambiguous data": ("Venue booking or block information needs clarification before equipment can be reserved.", 409),
    "Exactly one confirmed venue booking is required": ("Confirm one venue booking before reserving equipment.", 409),
    "Equipment proposal period must match the confirmed venue booking": ("The proposal period must match the confirmed venue booking. Revise the proposal and obtain agreement again.", 409),
    "Confirmed venue is unavailable for the proposed period": ("The venue is unavailable for this period.", 409),
    "Equipment schedule requires manual allocation review": ("This equipment schedule needs manual allocation review before it can be reserved.", 409),
    "Equipment proposal changed; reload before continuing": ("The proposal changed. Reload and review the latest quantity.", 409),
    "Current organiser agreement is required": ("The organiser must agree to the current proposal before reservation.", 409),
    "A positive suggested quantity is required": ("Enter a whole suggested quantity greater than zero.", 400),
    "Only the event organiser can agree to this proposal": ("Only this event's organiser can agree to the proposal.", 403),
    "Equipment proposal is not eligible": ("This event or equipment proposal is not eligible for this operation.", 409),
    "Venue and transfer validation is not configured": ("Final reservation is awaiting venue and transfer validation configuration.", 503),
    "Equipment unavailable, or stock is required for an earlier request":
        ("Equipment is unavailable or required for an earlier request.", 409),
    "Equipment commitments contain invalid or ambiguous data":
        ("Equipment commitments contain invalid or ambiguous data. Ask Technical Support to clarify them.", 409),
    "Equal or missing request timestamps need a confirmed priority decision":
        ("Equal or missing request timestamps require clarification before acceptance.", 409),
    "Equipment request not found or inaccessible": ("Equipment request not found or inaccessible.", 404),
    "Only requested equipment requests can be accepted": ("Only requested equipment requests can be accepted.", 409),
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


def ensure_organiser(client, user_id):
    roles = (client.table("user_role").select("role").eq("user_id", user_id)
             .eq("role", "event_organiser").limit(1).execute().data)
    if not roles:
        raise EquipmentError("Event Organiser access is required.", 403)


EVENT_FIELDS = (
    "event_id,organiser_id,name,status,description,technical_requirements,venue_requirements,"
    "technical_support_required,start_datetime,end_datetime,preferred_start_datetime,preferred_end_datetime,"
    "venue_booking(booking_id,venue_id,status,requested_start,requested_end,venue(name,location))"
)


def _integer(value, label, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise EquipmentError(f"{label} must be a whole number of at least {minimum}.")
    return value


def _period(start, end):
    try:
        a = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        if a.tzinfo is None or b.tzinfo is None or a >= b:
            raise ValueError()
    except (ValueError, TypeError):
        raise EquipmentError("Provide a valid start and end time with a timezone.") from None
    return a.isoformat(), b.isoformat()


def technical_context(client, user_id):
    """Include organiser events even before a separate equipment row exists."""
    ensure_technical_support(client, user_id)
    events = (client.table("event").select(EVENT_FIELDS)
              .or_("technical_support_required.eq.true,technical_requirements.not.is.null")
              .in_("status", ["approved", "confirmed"])
              .order("created_at").execute().data or [])
    equipment = (client.table("equipment").select("equipment_id,name,type,total_quantity")
                 .eq("active", True).order("name").execute().data or [])
    events = [event for event in events if event.get("status") in {"approved", "confirmed"}
              and (event.get("technical_support_required") or str(event.get("technical_requirements") or "").strip())]
    return {"events": events, "equipment": equipment}


def _rpc(client, name, params):
    try:
        return client.rpc(name, params).execute().data
    except APIError as exc:
        if exc.code in {"PGRST202", "PGRST204", "42883", "42703"}:
            raise EquipmentError(
                "The equipment workflow is not configured in the database. "
                "Contact the project team to complete setup.", 503
            ) from None
        if exc.message in RPC_ERRORS:
            message, status = RPC_ERRORS[exc.message]
            raise EquipmentError(message, status) from None
        if exc.code == "42501":
            raise EquipmentError("Equipment access is not permitted by your current permissions.", 403) from None
        raise EquipmentError("Unable to complete the equipment operation. Please try again.", 503) from None


def _related(client, reservation):
    event = (client.table("event").select(EVENT_FIELDS)
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
            .in_("status", ["requested", "reserved"]).order("requested_at").execute().data or [])
    # Do not silently hide a request whose related event is hidden by RLS.
    details = [_related(client, row) for row in rows]
    return [item for item in details if item["event"].get("status") in {"approved", "confirmed"}]


def get_request(client, user_id, reservation_id):
    """Reload one request's details under the Technical Support caller's RLS."""
    ensure_technical_support(client, user_id)
    details = _related(client, _request(client, reservation_id))
    if details["event"].get("status") not in {"approved", "confirmed"}:
        raise EquipmentError("Coordinator approval is required before Technical Support review.", 409)
    return details


def availability(client, user_id, reservation_id):
    ensure_technical_support(client, user_id)
    row = _request(client, reservation_id)
    details = _related(client, row)
    if row.get("status") != "requested" or details["event"].get("status") not in {"approved", "confirmed"}:
        raise EquipmentError("Only requested equipment requests for approved or confirmed events can be accepted.", 409)
    quantity = row.get("quantity_suggested")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise EquipmentError("Save a positive suggested quantity before checking availability.", 409)
    free = _rpc(client, "cs_equipment_request_available", {"p_reservation_id": validate_id(reservation_id)})
    if not isinstance(free, int) or isinstance(free, bool):
        raise EquipmentError("Unable to verify equipment availability.", 503)
    return {**details, "available_quantity": max(0, free), "sufficient_stock": free >= quantity}


def accept_request(client, user_id, reservation_id):
    ensure_technical_support(client, user_id)
    # Load presentation metadata before committing, so RLS gaps cannot turn a
    # saved reservation into a failed confirmation. The RPC decides acceptance.
    details = _related(client, _request(client, reservation_id))
    row = details["reservation"]
    if row.get("status") != "reserved" and not (
        row.get("quantity_suggested") and row.get("proposal_version", 0) > 0
        and row.get("organiser_agreed_version") == row.get("proposal_version")
        and row.get("organiser_agreed_by") and row.get("organiser_agreed_at")
    ):
        raise EquipmentError("The organiser must agree to the current proposal before reservation.", 409)
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


def _saved_proposal(result):
    if isinstance(result, list) and len(result) == 1:
        result = result[0]
    if not isinstance(result, dict) or not result.get("reservation_id"):
        raise EquipmentError("Unable to verify the saved proposal. Reload before retrying.", 503)
    return result


def propose_quantity(client, user_id, payload):
    ensure_technical_support(client, user_id)
    if not isinstance(payload, dict):
        raise EquipmentError("Provide equipment proposal details.")
    start, end = _period(payload.get("start_datetime"), payload.get("end_datetime"))
    reservation_id = payload.get("reservation_id")
    params = {
        "p_event_id": validate_id(payload.get("event_id")),
        "p_equipment_id": validate_id(payload.get("equipment_id")),
        "p_quantity_suggested": _integer(payload.get("quantity_suggested"), "Suggested quantity"),
        "p_start": start, "p_end": end,
        "p_reservation_id": validate_id(reservation_id) if reservation_id else None,
        "p_expected_version": _integer(payload.get("proposal_version"), "Proposal version", 0) if reservation_id else None,
    }
    # Metadata is checked before the write; the RPC rechecks authorisation itself.
    metadata = _related(client, {"event_id": params["p_event_id"], "equipment_id": params["p_equipment_id"]})
    saved = _saved_proposal(_rpc(client, "propose_equipment_quantity", params))
    return {**metadata, "reservation": saved}


def organiser_proposals(client, user_id):
    ensure_organiser(client, user_id)
    events = (client.table("event").select("event_id").eq("organiser_id", user_id).execute().data or [])
    if not events:
        return []
    rows = (client.table("equipment_reservation").select("*")
            .in_("event_id", [e["event_id"] for e in events])
            .in_("status", ["requested", "reserved"]).order("requested_at").execute().data or [])
    return [_related(client, row) for row in rows if row.get("quantity_suggested") is not None]


def agree_proposal(client, user_id, reservation_id, payload):
    ensure_organiser(client, user_id)
    if not isinstance(payload, dict):
        raise EquipmentError("Provide the proposal version you reviewed.")
    version = _integer(payload.get("proposal_version"), "Proposal version")
    details = _related(client, _request(client, reservation_id))
    if details["event"].get("organiser_id") != user_id:
        raise EquipmentError("Only this event's organiser can agree to the proposal.", 403)
    saved = _saved_proposal(_rpc(client, "agree_equipment_proposal", {
        "p_reservation_id": validate_id(reservation_id), "p_expected_version": version,
    }))
    return {**details, "reservation": saved}
