"""Event Assignment service.

The current repository does not contain the automatic-assignment mechanism.
This service provides read-only views of assignment state:
- a coordinator's Assigned Events list
- an event's assignment status for its organiser or assigned coordinator
"""

COORDINATOR_ROLE = "event_coordinator"

ASSIGNED_EVENT_COLUMNS = (
    "event_id, name, status, start_datetime, end_datetime, "
    "preferred_start_datetime, preferred_end_datetime, expected_attendance"
)


class EventAssignmentError(Exception):
    """Base error with an HTTP status code for the route layer."""

    status_code = 400


class AuthenticationError(EventAssignmentError):
    status_code = 401


class PermissionDeniedError(EventAssignmentError):
    status_code = 403


class EventNotFoundError(EventAssignmentError):
    status_code = 404


def get_current_user_id(client, access_token):
    """Resolve the Supabase Auth user id from the access token."""
    try:
        response = client.auth.get_user(access_token)
    except Exception as exc:
        raise AuthenticationError("Your session has expired. Please log in again.") from exc

    user = getattr(response, "user", None)
    if user is None:
        raise AuthenticationError("Your session has expired. Please log in again.")
    return str(user.id)


def has_role(client, user_id, role):
    """Check the user's own roles (allowed by the user_role RLS policy)."""
    response = (
        client.table("user_role")
        .select("role")
        .eq("user_id", user_id)
        .eq("role", role)
        .execute()
    )
    return bool(response.data)


def get_assigned_events(client, user_id):
    """Return the events currently assigned to this Event Coordinator."""
    if not has_role(client, user_id, COORDINATOR_ROLE):
        raise PermissionDeniedError("Only Event Coordinators can view assigned events.")

    response = (
        client.table("event")
        .select(ASSIGNED_EVENT_COLUMNS)
        .eq("coordinator_id", user_id)
        .order("preferred_start_datetime")
        .execute()
    )
    return [_to_assigned_event(row) for row in (response.data or [])]


def get_event_assignment(client, user_id, event_id):
    """Return whether an event has a coordinator, and the coordinator's name.

    Only the event's organiser or its assigned coordinator may view this.
    """
    response = (
        client.table("event")
        .select("event_id, name, status, organiser_id, coordinator_id")
        .eq("event_id", event_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        raise EventNotFoundError("Event not found.")

    event = rows[0]
    is_organiser = event.get("organiser_id") == user_id
    is_assigned_coordinator = event.get("coordinator_id") == user_id
    if not (is_organiser or is_assigned_coordinator):
        raise PermissionDeniedError("You do not have access to this event's assignment.")

    coordinator_id = event.get("coordinator_id")
    return {
        "event_id": event.get("event_id"),
        "name": event.get("name") or "Untitled event",
        "status": event.get("status"),
        "coordinator_assigned": coordinator_id is not None,
        "coordinator_name": _get_coordinator_name(client, coordinator_id),
    }


def _get_coordinator_name(client, coordinator_id):
    """Return the coordinator's name, or None if unassigned or not visible under RLS."""
    if not coordinator_id:
        return None
    response = (
        client.table("profile")
        .select("name")
        .eq("user_id", coordinator_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0].get("name") if rows else None


def _to_assigned_event(row):
    """Prefer confirmed dates; fall back to the organiser's preferred dates."""
    return {
        "event_id": row.get("event_id"),
        "name": row.get("name") or "Untitled event",
        "status": row.get("status"),
        "start": row.get("start_datetime") or row.get("preferred_start_datetime"),
        "end": row.get("end_datetime") or row.get("preferred_end_datetime"),
        "expected_attendance": row.get("expected_attendance"),
    }
