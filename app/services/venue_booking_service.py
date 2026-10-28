from datetime import UTC, date, datetime, time, timedelta, timezone
import re

from app.supabase_client import create_authenticated_supabase_client


SINGAPORE_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Singapore")
ACTIVE_BOOKING_STATUSES = ("requested", "tentative", "confirmed")


class VenueBookingError(Exception):
    """A safe, expected error that can be returned to the caller."""

    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def authenticated_venue_client(access_token, role):
    """Use the caller's JWT for every database operation, preserving RLS."""
    if not access_token:
        raise VenueBookingError("Authentication is required.", 401)
    client = create_authenticated_supabase_client(access_token)
    try:
        response = client.auth.get_user(access_token)
        user_id = response.user.id
        if not user_id:
            raise ValueError("Missing user")
    except Exception as exc:
        raise VenueBookingError("The authenticated session is invalid.", 401) from exc
    roles = (
        client.table("user_role")
        .select("role")
        .eq("user_id", user_id)
        .eq("role", role)
        .execute()
    )
    if not roles.data:
        raise VenueBookingError("You do not have permission to perform this action.", 403)
    return client, user_id


def validate_booking_payload(payload, require_venue=True):
    """Validate and normalize the browser-facing booking payload."""
    if not isinstance(payload, dict):
        raise VenueBookingError("Request body must be a JSON object.")
    required = ["event_id", "booking_date", "start_time", "end_time", "setup_layout"]
    if require_venue:
        required.insert(1, "venue_id")
    cleaned = {}
    for field in required:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise VenueBookingError(f"{field} must be a non-empty string.")
        cleaned[field] = value.strip()
    cleaned["requested_start"], cleaned["requested_end"] = validate_time_slot(
        cleaned["booking_date"], cleaned["start_time"], cleaned["end_time"]
    )
    return cleaned


def validate_time_slot(slot_date, start_time, end_time):
    try:
        if not isinstance(slot_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", slot_date):
            raise ValueError()
        parsed_date = date.fromisoformat(slot_date)
        parsed_times = []
        for value in (start_time, end_time):
            if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", value):
                raise ValueError()
            parsed_times.append(time.fromisoformat(value))
        start, end = parsed_times
    except ValueError as exc:
        raise VenueBookingError("Use a valid date (YYYY-MM-DD) and time (HH:MM or HH:MM:SS).") from exc
    if start >= end:
        raise VenueBookingError("End time must be after start time on the same date.")
    return (
        datetime.combine(parsed_date, start, SINGAPORE_TIMEZONE).isoformat(),
        datetime.combine(parsed_date, end, SINGAPORE_TIMEZONE).isoformat(),
    )


def _supports_layout(venue, setup_layout):
    layouts = venue.get("supported_layouts")
    if isinstance(layouts, list):
        supported = layouts
    elif isinstance(layouts, dict):
        supported = list(layouts.keys()) + list(layouts.values())
    else:
        return False
    requested = setup_layout.casefold()
    return any(
        isinstance(value, str) and value.casefold() == requested
        for value in supported
    )


def _has_sufficient_capacity(venue, event):
    expected_attendance = event.get("expected_attendance")
    capacity = venue.get("capacity")
    return not (
        isinstance(expected_attendance, int)
        and isinstance(capacity, int)
        and capacity < expected_attendance
    )


def _event_for_coordinator(supabase, event_id, user_id):
    response = (
        supabase.table("event")
        .select("*")
        .eq("event_id", event_id)
        .eq("coordinator_id", user_id)
        .execute()
    )
    if not response.data:
        raise VenueBookingError("Event not found or not assigned to this Coordinator.", 404)
    event = response.data[0]
    if event.get("status") != "planning":
        raise VenueBookingError(
            "Venue bookings can only be requested for approved events in planning status."
        )
    return event


def _eligible_venue(supabase, venue_id, event, setup_layout):
    response = (
        supabase.table("venue")
        .select("*")
        .eq("venue_id", venue_id)
        .eq("active", True)
        .execute()
    )
    if not response.data:
        raise VenueBookingError("The selected venue is unavailable.", 404)
    venue = response.data[0]
    if not _has_sufficient_capacity(venue, event):
        raise VenueBookingError("The selected venue does not have sufficient capacity.", 409)
    if not _supports_layout(venue, setup_layout):
        raise VenueBookingError("The selected venue does not support the requested layout.", 409)
    return venue


def execute_conflict_check(
    supabase,
    venue_id,
    requested_start,
    requested_end,
    exclude_booking_id=None,
):
    """Check half-open timestamp ranges against active bookings and venue blocks."""
    query = (
        supabase.table("venue_booking")
        .select("booking_id")
        .eq("venue_id", venue_id)
        .in_("status", ACTIVE_BOOKING_STATUSES)
        .lt("requested_start", requested_end)
        .gt("requested_end", requested_start)
    )
    if exclude_booking_id:
        query = query.neq("booking_id", exclude_booking_id)
    if query.execute().data:
        return True
    return bool(
        supabase.table("venue_block")
        .select("venue_block_id")
        .eq("venue_id", venue_id)
        .lt("start_datetime", requested_end)
        .gt("end_datetime", requested_start)
        .execute()
        .data
    )


def get_coordinator_booking_context(access_token):
    """Return assigned planning events, active venues, and persisted bookings."""
    supabase, user_id = authenticated_venue_client(access_token, "event_coordinator")
    events = (
        supabase.table("event")
        .select("*")
        .eq("coordinator_id", user_id)
        .eq("status", "planning")
        .execute()
        .data
        or []
    )
    venues = supabase.table("venue").select("*").eq("active", True).execute().data or []
    event_ids = [event["event_id"] for event in events]
    bookings = []
    if event_ids:
        bookings = (
            supabase.table("venue_booking")
            .select("*, venue(*)")
            .in_("event_id", event_ids)
            .execute()
            .data
            or []
        )
    return {
        "success": True,
        "events": events,
        "venues": venues,
        "bookings": bookings,
    }, 200


def list_available_venues(
    access_token,
    event_id,
    booking_date,
    start_time,
    end_time,
    setup_layout,
):
    payload = validate_booking_payload(
        {
            "event_id": event_id,
            "booking_date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
            "setup_layout": setup_layout,
        },
        require_venue=False,
    )
    supabase, user_id = authenticated_venue_client(access_token, "event_coordinator")
    event = _event_for_coordinator(supabase, payload["event_id"], user_id)
    venues = supabase.table("venue").select("*").eq("active", True).execute().data or []
    available = []
    for venue in venues:
        if not _has_sufficient_capacity(venue, event):
            continue
        if not _supports_layout(venue, payload["setup_layout"]):
            continue
        if not execute_conflict_check(
            supabase,
            venue["venue_id"],
            payload["requested_start"],
            payload["requested_end"],
        ):
            available.append(venue)
    return {"success": True, "venues": available}, 200


def submit_venue_booking_request(
    access_token, event_id, venue_id, booking_date, start_time, end_time, setup_layout
):
    """Create a requested booking, which acts as the tentative hold."""
    payload = validate_booking_payload(
        {
            "event_id": event_id,
            "venue_id": venue_id,
            "booking_date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
            "setup_layout": setup_layout,
        }
    )
    supabase, user_id = authenticated_venue_client(access_token, "event_coordinator")
    event = _event_for_coordinator(supabase, payload["event_id"], user_id)
    _eligible_venue(supabase, payload["venue_id"], event, payload["setup_layout"])
    existing = (
        supabase.table("venue_booking")
        .select("booking_id")
        .eq("event_id", payload["event_id"])
        .in_("status", ACTIVE_BOOKING_STATUSES)
        .execute()
    )
    if existing.data:
        raise VenueBookingError("This event already has an active venue arrangement.", 409)
    if execute_conflict_check(
        supabase,
        payload["venue_id"],
        payload["requested_start"],
        payload["requested_end"],
    ):
        raise VenueBookingError(
            "The selected venue slot is unavailable due to an existing booking or blackout period.",
            409,
        )
    layout_update = (
        supabase.table("event")
        .update({"layout_requirements": payload["setup_layout"]})
        .eq("event_id", payload["event_id"])
        .eq("coordinator_id", user_id)
        .execute()
    )
    if not layout_update.data:
        raise VenueBookingError("Unable to save the selected setup layout.", 409)
    booking_payload = {
        "venue_id": payload["venue_id"],
        "event_id": payload["event_id"],
        "requested_start": payload["requested_start"],
        "requested_end": payload["requested_end"],
        "status": "requested",
        "requested_by": user_id,
        "requested_at": datetime.now(UTC).isoformat(),
    }
    booking_res = supabase.table("venue_booking").insert(booking_payload).execute()
    if not booking_res.data:
        raise VenueBookingError("Failed to create venue booking request.", 500)
    return {
        "success": True,
        "message": "Venue booking request submitted successfully.",
        "booking": booking_res.data[0],
        "display_status": "Pending Venue Approval",
        "notification_sent": False,
        "warning": (
            "Booking saved, but Venue Staff notification is unavailable because the current "
            "database has no venue-to-staff assignment or notification insert policy."
        ),
    }, 201


def get_all_booking_requests(access_token):
    """Return venue booking requests for authenticated Venue Staff."""
    supabase, _ = authenticated_venue_client(access_token, "venue_staff")
    bookings = (
        supabase.table("venue_booking")
        .select("*, venue(*), event(*)")
        .order("requested_at", desc=False)
        .execute()
        .data
        or []
    )
    return {"success": True, "requests": bookings}, 200


def get_venue_staff_context(access_token):
    """Return the venue catalogue needed by authenticated Venue Staff tools."""
    supabase, _ = authenticated_venue_client(access_token, "venue_staff")
    venues = supabase.table("venue").select("*").execute().data or []
    return {"success": True, "venues": venues}, 200


def _get_booking(supabase, booking_id):
    response = (
        supabase.table("venue_booking")
        .select("*")
        .eq("booking_id", booking_id)
        .execute()
    )
    if not response.data:
        raise VenueBookingError("Booking request not found.", 404)
    return response.data[0]


def _update_pending_booking(supabase, booking, update):
    if booking.get("status") not in ("requested", "tentative"):
        raise VenueBookingError("Only pending requests can be decided.", 409)
    updated = (
        supabase.table("venue_booking")
        .update(update)
        .eq("booking_id", booking["booking_id"])
        .eq("status", booking["status"])
        .execute()
    )
    if not updated.data:
        raise VenueBookingError("The booking changed. Refresh before trying again.", 409)
    return updated.data[0]


def _decision_response(message, booking):
    return {
        "success": True,
        "message": message,
        "booking": booking,
        "notification_sent": False,
        "warning": (
            "The Coordinator could not be notified under the current "
            "notification RLS policy."
        ),
    }, 200


def approve_venue_booking_request(access_token, booking_id):
    supabase, user_id = authenticated_venue_client(access_token, "venue_staff")
    booking = _get_booking(supabase, booking_id)
    if booking.get("status") not in ("requested", "tentative"):
        raise VenueBookingError("Only pending requests can be approved.", 409)
    if execute_conflict_check(
        supabase,
        booking["venue_id"],
        booking["requested_start"],
        booking["requested_end"],
        exclude_booking_id=booking_id,
    ):
        raise VenueBookingError("Cannot approve a conflicting venue request.", 409)
    updated_booking = _update_pending_booking(
        supabase,
        booking,
        {
            "status": "confirmed",
            "decided_by": user_id,
            "decided_at": datetime.now(UTC).isoformat(),
            "decision_reason": None,
        },
    )
    return _decision_response("Booking request approved.", updated_booking)


def _decision_reason(reason, alternative_venue_ids):
    reason_text = reason.strip() if isinstance(reason, str) else ""
    alternatives = [value.strip() for value in (alternative_venue_ids or [])]
    parts = [f"Reason: {reason_text or 'Not provided'}"]
    if alternatives:
        parts.append(f"Suggested alternatives: {', '.join(alternatives)}")
    return "\n".join(parts)


def reject_venue_booking_request(access_token, booking_id, reason=None, alternative_venue_ids=None):
    if reason is not None and not isinstance(reason, str):
        raise VenueBookingError("reason must be a string.")
    if alternative_venue_ids is not None and (
        not isinstance(alternative_venue_ids, list)
        or any(not isinstance(value, str) or not value.strip() for value in alternative_venue_ids)
    ):
        raise VenueBookingError("alternative_venue_ids must be a list of venue IDs.")
    supabase, user_id = authenticated_venue_client(access_token, "venue_staff")
    booking = _get_booking(supabase, booking_id)
    if booking.get("status") not in ("requested", "tentative"):
        raise VenueBookingError("Only pending requests can be rejected.", 409)
    updated_booking = _update_pending_booking(
        supabase,
        booking,
        {
            "status": "rejected",
            "decided_by": user_id,
            "decided_at": datetime.now(UTC).isoformat(),
            "decision_reason": _decision_reason(reason, alternative_venue_ids),
        },
    )
    return _decision_response("Booking request rejected.", updated_booking)


def block_venue_availability(
    access_token,
    venue_id,
    block_date,
    start_time,
    end_time,
    reason=None,
):
    requested_start, requested_end = validate_time_slot(block_date, start_time, end_time)
    if reason is not None and not isinstance(reason, str):
        raise VenueBookingError("reason must be a string.")
    supabase, user_id = authenticated_venue_client(access_token, "venue_staff")
    confirmed_overlap = (
        supabase.table("venue_booking")
        .select("booking_id")
        .eq("venue_id", venue_id)
        .eq("status", "confirmed")
        .lt("requested_start", requested_end)
        .gt("requested_end", requested_start)
        .execute()
    )
    if confirmed_overlap.data:
        raise VenueBookingError(
            "Cannot block a venue slot that overlaps a confirmed booking.", 409
        )
    payload = {
        "venue_id": venue_id,
        "start_datetime": requested_start,
        "end_datetime": requested_end,
        "reason": (reason.strip() or None) if isinstance(reason, str) else None,
        "created_by": user_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "active",
    }
    response = supabase.table("venue_block").insert(payload).execute()
    if not response.data:
        raise VenueBookingError("Failed to create venue blackout block.", 500)
    return {
        "success": True,
        "message": "Venue block created successfully.",
        "block": response.data[0],
    }, 201


def update_venue_details(
    access_token,
    venue_id,
    capacity=None,
    supported_layouts=None,
    accessibility=None,
):
    if capacity is not None and (type(capacity) is not int or capacity <= 0):
        raise VenueBookingError("capacity must be a positive integer.")
    if supported_layouts is not None and (
        not isinstance(supported_layouts, list)
        or any(not isinstance(value, str) or not value.strip() for value in supported_layouts)
    ):
        raise VenueBookingError("supported_layouts must be a list of layout names.")
    if accessibility is not None and (not isinstance(accessibility, str) or not accessibility.strip()):
        raise VenueBookingError("accessibility must be a non-empty string.")
    if capacity is None and supported_layouts is None and accessibility is None:
        raise VenueBookingError("Provide at least one venue detail to update.")
    supabase, _ = authenticated_venue_client(access_token, "venue_staff")
    payload = {}
    if capacity is not None:
        payload["capacity"] = capacity
    if supported_layouts is not None:
        payload["supported_layouts"] = [value.strip() for value in supported_layouts]
    if accessibility is not None:
        payload["accessibility"] = accessibility.strip()
    response = (
        supabase.table("venue")
        .update(payload)
        .eq("venue_id", venue_id)
        .execute()
    )
    if not response.data:
        raise VenueBookingError("Venue not found or could not be updated.", 404)
    return {"success": True, "message": "Venue details updated.", "venue": response.data[0]}, 200


def get_venue_schedule(access_token, venue_id):
    supabase, _ = authenticated_venue_client(access_token, "venue_staff")
    bookings = (
        supabase.table("venue_booking")
        .select("*")
        .eq("venue_id", venue_id)
        .execute()
    )
    blocks = (
        supabase.table("venue_block")
        .select("*")
        .eq("venue_id", venue_id)
        .execute()
    )
    return {
        "success": True,
        "schedule": {
            "bookings_and_holds": bookings.data or [],
            "maintenance_blocks": blocks.data or [],
        },
    }, 200
