"""B1 application adapter; all database work uses the caller's JWT."""

from uuid import UUID

from app.services.venue_booking_service import VenueBookingError, authenticated_venue_client
from app.services.venue_occupancy import configuration, validate_minutes


class VenueBufferError(VenueBookingError):
    def __init__(self, code, message, status_code=400):
        super().__init__(message, status_code)
        self.code = code


def _uuid(value, field):
    try:
        if not isinstance(value, str):
            raise ValueError()
        return str(UUID(value))
    except (ValueError, AttributeError) as exc:
        raise VenueBufferError("B1_INVALID_INPUT", f"{field} must be a UUID.") from exc


def read_venue_buffers(access_token, venue_id):
    venue_id = _uuid(venue_id, "venue_id")
    client, _ = authenticated_venue_client(access_token, "venue_staff")
    rows = client.table("venue").select("venue_id,setup_minutes,turnaround_minutes,buffer_config_revision").eq("venue_id", venue_id).execute().data
    if not rows:
        raise VenueBufferError("B1_VENUE_NOT_FOUND", "Venue not found.", 404)
    return {"success": True, "venue_id": venue_id, **configuration(rows[0])}


def read_buffer_notifications(access_token):
    """Read only this Coordinator's B1 notices through existing recipient RLS."""
    client, user_id = authenticated_venue_client(access_token, "event_coordinator")
    rows = (client.table("notification").select("notification_id,event_id,type,message,created_at,read_at")
            .eq("recipient_id", user_id).eq("type", "venue_buffer_conflict")
            .order("created_at", desc=True).execute().data or [])
    return {"success": True, "notifications": rows}


_DATABASE_ERRORS = {
    "B1_VENUE_STAFF_REQUIRED": (403, "Venue Staff access is required."),
    "B1_STALE_CONFIGURATION_REVISION": (409, "Configuration changed. Refresh and review before saving again."),
    "B1_OPERATION_TOKEN_REUSED": (409, "The operation ID belongs to another intent. Use a new ID for a new edit."),
    "B1_AUTHORITATIVE_OCCUPANCY_UNASSESSABLE": (409, "Authoritative venue occupancy cannot be assessed. Its owner must resolve the data or block scope before saving."),
    "B1_ZERO_DECISION_REQUIRED": (409, "Zero duration requires a separate business decision."),
    "B1_VENUE_NOT_FOUND": (404, "Venue not found."),
    "B1_REVISION_EXHAUSTED": (409, "Configuration revision requires administrator review."),
    "B1_DATETIME_OUTSIDE_COMMON_SUPPORTED_RANGE": (409, "Occupied period exceeds the supported datetime range."),
    "B1_CONFIGURATION_REQUIRED": (409, "Venue durations are unconfigured."),
    "B1_INVALID_SCHEDULE": (409, "Authoritative scheduled times require review."),
    "B1_NEGATIVE_DURATION": (400, "Durations must be nonnegative whole integer minutes."),
    "B1_REQUIRED_INPUT_MISSING_OR_INVALID": (400, "Required configuration input is missing or invalid."),
}


def save_venue_buffers(access_token, venue_id, payload):
    venue_id = _uuid(venue_id, "venue_id")
    fields = {"setup_minutes", "turnaround_minutes", "expected_revision", "operation_id"}
    if not isinstance(payload, dict) or set(payload) != fields:
        raise VenueBufferError("B1_INVALID_INPUT", "Supply only setup_minutes, turnaround_minutes, expected_revision and operation_id.")
    operation_id = _uuid(payload["operation_id"], "operation_id")
    revision = payload["expected_revision"]
    if type(revision) is not int or not 0 <= revision <= 9223372036854775807:
        raise VenueBufferError("B1_INVALID_INPUT", "expected_revision must be a nonnegative integer.")
    for name in ("setup_minutes", "turnaround_minutes"):
        if payload[name] is None:
            raise VenueBufferError("B1_INVALID_INPUT", "Both duration values are required.")
        validate_minutes(payload[name])
    client, _ = authenticated_venue_client(access_token, "venue_staff")
    try:
        outcome = client.rpc("b1_save_venue_buffers", {
            "p_venue_id": venue_id, "p_setup_minutes": payload["setup_minutes"],
            "p_turnaround_minutes": payload["turnaround_minutes"],
            "p_expected_revision": revision, "p_operation_id": operation_id,
        }).execute().data
    except Exception as exc:
        # Classify known database messages; never return SQL DETAIL/HINT or raw text.
        message = str(getattr(exc, "message", "") or exc)
        for code, (status, public_message) in _DATABASE_ERRORS.items():
            if code in message:
                raise VenueBufferError(code, public_message, status) from exc
        if str(getattr(exc, "code", "")) in ("42501", "PGRST202"):
            raise VenueBufferError("B1_CAPABILITY_DISABLED", "Buffer saving is not enabled for application callers.", 503) from exc
        raise VenueBufferError("B1_SAVE_UNCONFIRMED", "Unable to confirm the save. Retry the same operation ID and values.", 503) from exc
    if not isinstance(outcome, dict) or outcome.get("configuration_saved") is not True:
        raise VenueBufferError("B1_SAVE_UNCONFIRMED", "Unable to confirm the save. Retry the same operation ID and values.", 503)
    return {"success": True, **outcome}
