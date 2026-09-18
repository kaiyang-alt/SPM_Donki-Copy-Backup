from app.supabase_client import create_authenticated_supabase_client


EVENT_CHANGE_PENDING_STATUS = "pending"


class EventChangeRequestAccessError(Exception):
    """Raised when an authenticated change-request operation fails."""

    def __init__(self, message, original_error=None):
        super().__init__(message)
        self.original_error = original_error


class EventChangeRequestNotFoundError(Exception):
    """Raised when RLS does not expose the requested event."""


class EventChangeRequestValidationError(Exception):
    """Raised when required change-request details are missing."""


def list_change_request_events(access_token: str) -> list[dict]:
    try:
        client = create_authenticated_supabase_client(access_token)
        client.auth.get_user(access_token)
        response = client.table("event").select("*").execute()
        return response.data or []
    except Exception as exc:
        raise EventChangeRequestAccessError(
            "Unable to load authorised events."
        ) from exc


def create_event_change_request(access_token: str, payload: dict) -> dict:
    event_id = str(payload.get("event_id", "")).strip()
    change_details = str(payload.get("change_details", "")).strip()

    if not event_id:
        raise EventChangeRequestNotFoundError("Event not found.")

    if not change_details:
        raise EventChangeRequestValidationError("Change details are required.")

    try:
        client = create_authenticated_supabase_client(access_token)

        existing_response = (
            client.table("event")
            .select("*")
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        if not existing_response.data:
            raise EventChangeRequestNotFoundError("Event not found.")

        user_response = client.auth.get_user(access_token)
        user_id = user_response.user.id

        insert_payload = {
            "event_id": event_id,
            "requested_by": user_id,
            "proposed_changes": _proposed_changes(payload),
            "reason": change_details,
            "status": EVENT_CHANGE_PENDING_STATUS,
        }

        response = (
            client.table("event_change_request")
            .insert(insert_payload)
            .execute()
        )
    except EventChangeRequestNotFoundError:
        raise
    except Exception as exc:
        raise EventChangeRequestAccessError(
            "Unable to submit the change request.", exc
        ) from exc

    if not response.data:
        raise EventChangeRequestAccessError("Unable to submit the change request.")

    return response.data[0]


def _proposed_changes(payload: dict) -> dict:
    return {
        "date": _clean(payload.get("date")),
        "time": _clean(payload.get("time")),
        "expected_attendance": payload.get("expected_attendance"),
        "programme_timings": _clean(payload.get("programme_timings")),
        "venue_requirements": _clean(payload.get("venue_requirements")),
        "equipment_requirements": _clean(payload.get("equipment_requirements")),
        "technical_support_requirements": _clean(
            payload.get("technical_support_requirements")
        ),
    }


def _clean(value):
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None
