from app.supabase_client import create_authenticated_supabase_client


class EventAccessError(Exception):
    """Raised when an authenticated event operation cannot be completed."""


class EventNotFoundError(Exception):
    """Raised when RLS does not expose the requested event to the user."""


class EventNotEditableError(Exception):
    """Raised when an organiser attempts to modify a non-editable event."""


def list_authorised_events(access_token: str) -> list[dict]:
    try:
        client = create_authenticated_supabase_client(access_token)
        client.auth.get_user(access_token)
        response = client.table("event").select("*").execute()
        return response.data or []
    except Exception as exc:
        raise EventAccessError("Unable to load authorised events.") from exc


def update_authorised_event_name(
    access_token: str, event_id: str, event_name: str
) -> dict:
    try:
        client = create_authenticated_supabase_client(access_token)
        client.auth.get_user(access_token)
        existing_response = (
            client.table("event")
            .select("*")
            .eq("event_id", event_id)
            .limit(1)
            .execute()
        )
        if not existing_response.data:
            raise EventNotFoundError("Event not found.")

        existing_event = existing_response.data[0]
        editable_statuses = {"draft", "requested", "changes_requested"}

        if existing_event.get("status") not in editable_statuses:
            raise EventNotEditableError(
                "The event cannot be edited in its current status."
            )

        response = (
            client.table("event")
            .update({"name": event_name})
            .eq("event_id", event_id)
            .execute()
        )
    except EventNotFoundError:
        raise
    except EventAccessError:
        raise
    except EventNotEditableError:
        raise
    except Exception as exc:
        raise EventAccessError("Unable to update the event.") from exc

    if not response.data:
        raise EventNotFoundError("Event not found.")

    return response.data[0]
