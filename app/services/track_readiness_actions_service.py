"""Business logic for the "Track Event Readiness and Outstanding Actions" user story.

Flow: route -> this service -> Supabase (via the caller's authenticated client,
so existing Row Level Security applies).
"""

from datetime import date, datetime, timezone

EVENT_TABLE = "event"
VENUE_BOOKING_TABLE = "venue_booking"
EQUIPMENT_RESERVATION_TABLE = "equipment_reservation"
EQUIPMENT_TABLE = "equipment"
USER_ROLE_TABLE = "user_role"

COORDINATOR_ROLE = "event_coordinator"

# Existing approved status values only (project_context.md sections 5 and 6).
EVENT_STATUS_APPROVED = "approved"      # only status from which an event can be confirmed
EVENT_STATUS_CONFIRMED = "confirmed"
VENUE_BOOKING_CONFIRMED = "confirmed"
VENUE_BOOKING_INACTIVE = {"rejected", "cancelled"}
# Display label "Confirmed" for an equipment reservation is stored as `reserved`
# (technical support sets it when they accept the request).
EQUIPMENT_RESERVATION_CONFIRMED = "reserved"
EQUIPMENT_RESERVATION_INACTIVE = {"cancelled"}

# Explicit "no equipment" choice, recorded in event.technical_requirements.
NO_EQUIPMENT_REQUIRED_TEXT = "no equipment required"

# Display labels (not stored status values).
READINESS_INCOMPLETE = "Incomplete"
READINESS_READY = "Ready for Confirmation"
TASK_COMPLETED = "completed"


class ReadinessError(Exception):
    def __init__(self, message, status_code=400, readiness=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.readiness = readiness

    def to_dict(self):
        body = {"error": self.message}
        if self.readiness is not None:
            body["readiness"] = self.readiness
        return body


# ---------------------------------------------------------------------------
# Data sources that do not exist in the current schema.
# Programme setup and event tasks have no table or column yet, so nothing is
# tracked. Replace ONLY these two functions when the team approves a source.
#   programme setup -> a status string, e.g. "completed"
#   event tasks     -> list of {"name", "responsible", "deadline", "status"}
# ---------------------------------------------------------------------------
def _load_programme_status(client, event):
    return None


def _load_tasks(client, event):
    return []


# ---------------------------------------------------------------------------
# Condition evaluation (pure functions)
# ---------------------------------------------------------------------------
def _condition(label, complete, detail, **extra):
    return {"label": label, "complete": complete, "detail": detail, **extra}


def _action(kind, message):
    return {"type": kind, "message": message}


def _evaluate_venue(bookings):
    active = [b for b in bookings if b.get("status") not in VENUE_BOOKING_INACTIVE]
    if any(b.get("status") == VENUE_BOOKING_CONFIRMED for b in active):
        return _condition("Venue booking", True, "Venue booking is confirmed."), []
    if not active:
        detail = "No venue booking has been requested."
        return _condition("Venue booking", False, detail), [
            _action("venue", "Request a venue booking and get it confirmed.")
        ]
    status = active[0].get("status") or "unknown"
    detail = f"Venue booking is {status}, not confirmed."
    return _condition("Venue booking", False, detail), [
        _action("venue", f"Venue booking is {status}; it must be confirmed.")
    ]


def _records_no_equipment(technical_requirements):
    text = (technical_requirements or "").strip().lower().rstrip(".")
    return text == NO_EQUIPMENT_REQUIRED_TEXT


def _evaluate_equipment(event, reservations):
    active = [r for r in reservations if r.get("status") not in EQUIPMENT_RESERVATION_INACTIVE]
    pending = [r for r in active if r.get("status") != EQUIPMENT_RESERVATION_CONFIRMED]

    if pending:
        actions = [
            _action(
                "equipment",
                f"Equipment reservation for {r.get('equipment_name') or 'equipment'} "
                f"is {r.get('status') or 'unknown'}; it must be confirmed.",
            )
            for r in pending
        ]
        return _condition("Equipment reservations", False,
                          f"{len(pending)} of {len(active)} required reservation(s) not confirmed."), actions
    if active:
        return _condition("Equipment reservations", True, "Every required reservation is confirmed."), []
    if _records_no_equipment(event.get("technical_requirements")):
        return _condition("Equipment reservations", True, "No equipment required."), []
    return _condition(
        "Equipment reservations", False,
        "No equipment reservation exists and 'No equipment required' is not recorded.",
    ), [_action("equipment", "Reserve the required equipment, or record 'No equipment required'.")]


def _evaluate_programme(status):
    if status is None:
        return _condition("Programme setup", True, "Not tracked in the current system.", tracked=False), []
    if str(status).strip().lower() == TASK_COMPLETED:
        return _condition("Programme setup", True, "Programme setup is completed.", tracked=True), []
    return _condition("Programme setup", False, f"Programme setup is {status}, not completed.", tracked=True), [
        _action("programme", f"Programme setup is {status}; it must be completed.")
    ]


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _evaluate_tasks(tasks, today):
    unfinished = []
    for task in tasks:
        if str(task.get("status") or "").strip().lower() == TASK_COMPLETED:
            continue
        deadline = _as_date(task.get("deadline"))
        unfinished.append({
            "name": task.get("name"),
            "responsible": task.get("responsible"),
            "deadline": task.get("deadline"),
            "status": task.get("status"),
            "overdue": bool(deadline and deadline < today),
        })
    if not unfinished:
        detail = "All tasks are completed." if tasks else "No tasks exist."
        return _condition("Event tasks", True, detail), [], []
    actions = [
        _action("task", f"Task '{t['name']}' is not completed" + (" (Overdue)." if t["overdue"] else "."))
        for t in unfinished
    ]
    return _condition("Event tasks", False, f"{len(unfinished)} task(s) not completed."), actions, unfinished


# ---------------------------------------------------------------------------
# Supabase access
# ---------------------------------------------------------------------------
def ensure_coordinator(client, user_id):
    response = (
        client.table(USER_ROLE_TABLE)
        .select("*")
        .eq("user_id", user_id)
        .eq("role", COORDINATOR_ROLE)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise ReadinessError("Only Event Coordinators can view event readiness.", 403)


def _get_assigned_event(client, user_id, event_id):
    response = (
        client.table(EVENT_TABLE)
        .select("*")
        .eq("event_id", event_id)
        .eq("coordinator_id", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise ReadinessError("Event not found or not assigned to you.", 404)
    return response.data[0]


def _equipment_names(client, reservations):
    ids = list({r["equipment_id"] for r in reservations if r.get("equipment_id")})
    if not ids:
        return {}
    response = client.table(EQUIPMENT_TABLE).select("equipment_id,name").in_("equipment_id", ids).execute()
    return {row["equipment_id"]: row.get("name") for row in (response.data or [])}


def _event_summary(event):
    return {
        "event_id": event.get("event_id"),
        "name": event.get("name"),
        "status": event.get("status"),
        "start_datetime": event.get("start_datetime") or event.get("preferred_start_datetime"),
    }


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------
def list_assigned_events(client, user_id):
    ensure_coordinator(client, user_id)
    response = client.table(EVENT_TABLE).select("*").eq("coordinator_id", user_id).execute()
    return [_event_summary(row) for row in (response.data or [])]


def _build_readiness(client, event, today):
    event_id = event["event_id"]
    bookings = (
        client.table(VENUE_BOOKING_TABLE).select("*").eq("event_id", event_id).execute().data or []
    )
    reservations = (
        client.table(EQUIPMENT_RESERVATION_TABLE).select("*").eq("event_id", event_id).execute().data or []
    )
    names = _equipment_names(client, reservations)
    reservations = [{**r, "equipment_name": names.get(r.get("equipment_id"))} for r in reservations]

    venue, venue_actions = _evaluate_venue(bookings)
    equipment, equipment_actions = _evaluate_equipment(event, reservations)
    programme, programme_actions = _evaluate_programme(_load_programme_status(client, event))
    tasks, task_actions, unfinished = _evaluate_tasks(_load_tasks(client, event) or [], today)

    conditions = {"venue": venue, "equipment": equipment, "programme": programme, "tasks": tasks}
    ready = all(c["complete"] for c in conditions.values())
    return {
        "event": _event_summary(event),
        "readiness": READINESS_READY if ready else READINESS_INCOMPLETE,
        "can_confirm": ready and event.get("status") == EVENT_STATUS_APPROVED,
        "conditions": conditions,
        "outstanding_actions": venue_actions + equipment_actions + programme_actions + task_actions,
        "unfinished_tasks": unfinished,
        "venue_bookings": [{"status": b.get("status")} for b in bookings],
        "equipment_reservations": [
            {"equipment_name": r.get("equipment_name"), "status": r.get("status"),
             "quantity_requested": r.get("quantity_requested")}
            for r in reservations
        ],
    }


def get_readiness(client, user_id, event_id, today=None):
    ensure_coordinator(client, user_id)
    event = _get_assigned_event(client, user_id, event_id)
    return _build_readiness(client, event, today or datetime.now(timezone.utc).date())


def confirm_event(client, user_id, event_id, today=None):
    """Re-check current readiness, then move an `approved` event to `confirmed`."""
    ensure_coordinator(client, user_id)
    event = _get_assigned_event(client, user_id, event_id)
    readiness = _build_readiness(client, event, today or datetime.now(timezone.utc).date())

    if event.get("status") != EVENT_STATUS_APPROVED:
        raise ReadinessError(
            f"Only events with status '{EVENT_STATUS_APPROVED}' can be confirmed.", 409, readiness
        )
    if readiness["readiness"] != READINESS_READY:
        raise ReadinessError(
            "The event cannot be confirmed until all outstanding actions are completed.", 409, readiness
        )

    response = (
        client.table(EVENT_TABLE)
        .update({"status": EVENT_STATUS_CONFIRMED, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("event_id", event_id)
        .eq("coordinator_id", user_id)
        .eq("status", EVENT_STATUS_APPROVED)  # guards against a concurrent status change
        .execute()
    )
    if not response.data:
        raise ReadinessError("The event status changed. Refresh and try again.", 409, readiness)
    return _event_summary(response.data[0])
