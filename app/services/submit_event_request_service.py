"""Business logic for the "Submit Event Request" user story.

Flow: route -> this service -> Supabase (via the caller's authenticated client,
so existing Row Level Security applies).
"""

from datetime import datetime, timezone

EVENT_TABLE = "event"
USER_ROLE_TABLE = "user_role"

# Existing approved status values only (project_context.md section 5).
STATUS_DRAFT = "draft"
STATUS_REQUESTED = "requested"

ORGANISER_ROLE = "event_organiser"

# API field -> column in public.event (matches the documented schema).
COLUMN_MAP = {
    "name": "name",
    "description": "description",
    "purpose": "purpose",
    "expected_attendance": "expected_attendance",
    "venue_requirements": "venue_requirements",
    "layout_requirements": "layout_requirements",
    "accessibility_needs": "accessibility_needs",
    "technical_support_required": "technical_support_required",
    "technical_requirements": "technical_requirements",
    "registration_enabled": "registration_enabled",
    "preferred_start_datetime": "preferred_start_datetime",
    "preferred_end_datetime": "preferred_end_datetime",
}
BOOLEAN_FIELDS = {"technical_support_required", "registration_enabled"}
DATETIME_FIELDS = ("preferred_start_datetime", "preferred_end_datetime")

# Required to submit (nullable in the database only so drafts can be saved).
MANDATORY_FIELDS = {
    "name": "Event name",
    "preferred_start_datetime": "Preferred start date and time",
    "preferred_end_datetime": "Preferred end date and time",
    "expected_attendance": "Expected number of attendees",
}


class EventRequestError(Exception):
    def __init__(self, message, status_code=400, missing_fields=None, invalid_fields=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.missing_fields = missing_fields or []
        self.invalid_fields = invalid_fields or []

    def to_dict(self):
        body = {"error": self.message}
        if self.missing_fields:
            body["missing_fields"] = self.missing_fields
        if self.invalid_fields:
            body["invalid_fields"] = self.invalid_fields
        return body


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _clean(data):
    """Keep only known fields; trim strings; empty -> None."""
    data = data or {}
    cleaned = {}
    for field in COLUMN_MAP:
        value = data.get(field)
        if field in BOOLEAN_FIELDS:
            cleaned[field] = (
                None if value is None else (value is True or str(value).lower() == "true")
            )
            continue
        if isinstance(value, str):
            value = value.strip()
        cleaned[field] = None if value in ("", None) else value
    return cleaned


def _bad(field, message):
    return {"field": field, "message": message}


def _parse_datetime(value):
    """Parse an ISO-8601 timestamp that carries a timezone; return it in UTC."""
    parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _validate_formats(cleaned):
    """Validate values in place; datetimes become UTC ISO strings."""
    invalid = []

    attendance = cleaned.get("expected_attendance")
    if attendance is not None:
        try:
            number = int(attendance)
            if number <= 0:
                raise ValueError
            cleaned["expected_attendance"] = number
        except (TypeError, ValueError):
            invalid.append(_bad("expected_attendance", "Enter a whole number greater than 0."))

    parsed = {}
    for field in DATETIME_FIELDS:
        if cleaned[field] is None:
            continue
        try:
            parsed[field] = _parse_datetime(cleaned[field])
        except ValueError:
            invalid.append(_bad(field, "Enter a valid date and time."))

    start = parsed.get("preferred_start_datetime")
    end = parsed.get("preferred_end_datetime")
    if start and end and end <= start:
        invalid.append(_bad("preferred_end_datetime", "End time must be after the start time."))

    if invalid:
        raise EventRequestError("Some fields have invalid values.", 422, invalid_fields=invalid)

    for field, value in parsed.items():
        cleaned[field] = value.isoformat()


def _missing_mandatory(cleaned):
    return [
        {"field": field, "label": label}
        for field, label in MANDATORY_FIELDS.items()
        if cleaned.get(field) is None
    ]


def _to_row(cleaned):
    return {COLUMN_MAP[field]: value for field, value in cleaned.items()}


def _from_row(row):
    result = {"event_id": row.get("event_id"), "status": row.get("status")}
    for field, column in COLUMN_MAP.items():
        result[field] = row.get(column)
    return result


def ensure_organiser(client, user_id):
    response = (
        client.table(USER_ROLE_TABLE)
        .select("*")
        .eq("user_id", user_id)
        .eq("role", ORGANISER_ROLE)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise EventRequestError("Only Event Organisers can submit event requests.", 403)


def _persist(client, user_id, cleaned, event_id, status):
    now = datetime.now(timezone.utc).isoformat()  # created_at/updated_at have no DB default
    row = _to_row(cleaned)
    row["status"] = status
    row["updated_at"] = now

    if event_id:
        response = (
            client.table(EVENT_TABLE)
            .update(row)
            .eq("event_id", event_id)
            .eq("organiser_id", user_id)
            .eq("status", STATUS_DRAFT)  # only drafts can be edited/submitted here
            .execute()
        )
        if not response.data:
            raise EventRequestError("Draft not found or can no longer be edited.", 404)
    else:
        row["organiser_id"] = user_id
        row["created_at"] = now
        response = client.table(EVENT_TABLE).insert(row).execute()
        if not response.data:
            raise EventRequestError("The request could not be saved.", 500)

    return _from_row(response.data[0])


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------
def save_draft(client, user_id, data):
    """Save an incomplete request with status `draft` (create or update)."""
    ensure_organiser(client, user_id)
    cleaned = _clean(data)
    _validate_formats(cleaned)
    return _persist(client, user_id, cleaned, (data or {}).get("event_id"), STATUS_DRAFT)


def submit_request(client, user_id, data):
    """Submit a complete request; resulting status is `requested`."""
    ensure_organiser(client, user_id)
    cleaned = _clean(data)

    missing = _missing_mandatory(cleaned)
    if missing:
        raise EventRequestError(
            "Complete the required fields before submitting.", 422, missing_fields=missing
        )
    _validate_formats(cleaned)

    return _persist(client, user_id, cleaned, (data or {}).get("event_id"), STATUS_REQUESTED)


def list_requests(client, user_id):
    ensure_organiser(client, user_id)
    response = client.table(EVENT_TABLE).select("*").eq("organiser_id", user_id).execute()
    return [_from_row(row) for row in (response.data or [])]


def get_request(client, user_id, event_id):
    ensure_organiser(client, user_id)
    response = (
        client.table(EVENT_TABLE)
        .select("*")
        .eq("event_id", event_id)
        .eq("organiser_id", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise EventRequestError("Event request not found.", 404)
    return _from_row(response.data[0])