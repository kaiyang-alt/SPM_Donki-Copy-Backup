from app.supabase_client import create_authenticated_supabase_client
from app.services.venue_occupancy import assess_schedule, load_occupancy_rows


CONFIRMED_STATUS = "confirmed"
TENTATIVE_STATUSES = {"requested", "tentative"}
BLOCK_STATUS = "blocked"


class VenueAvailabilityAccessError(Exception):
    """Raised when the authenticated user lacks Venue Staff access."""


class VenueAvailabilityValidationError(Exception):
    """Raised when block details are missing or malformed."""


class VenueAvailabilityOverlapError(Exception):
    """Raised when a block overlaps a confirmed booking."""


def _venue_staff_client(access_token: str):
    client = create_authenticated_supabase_client(access_token)
    user = client.auth.get_user(access_token).user
    role = (
        client.table("user_role")
        .select("role")
        .eq("user_id", user.id)
        .eq("role", "venue_staff")
        .limit(1)
        .execute()
    )
    if not role.data:
        raise VenueAvailabilityAccessError("Venue Staff access required.")
    return client


def get_venue_availability(access_token: str, venue_id: str) -> dict:
    client = _venue_staff_client(access_token)

    bookings, bookings_complete = load_occupancy_rows(client, "venue_booking", venue_id)
    blocks, blocks_complete = load_occupancy_rows(client, "venue_block", venue_id)

    venues = client.table("venue").select("*").eq("venue_id", venue_id).execute().data or []
    assessment = assess_schedule(venues[0] if venues else {}, bookings, blocks, bookings_complete and blocks_complete)
    confirmed = [b for b in assessment["bookings_and_holds"] if b.get("status") == CONFIRMED_STATUS]
    tentative = [
        b for b in assessment["bookings_and_holds"] if b.get("status") in TENTATIVE_STATUSES
    ]

    return {
        **assessment,
        "venue_id": venue_id,
        "confirmed_bookings": confirmed,
        "tentative_holds": tentative,
        "blocks": blocks,
    }


def list_venue_blocks(access_token: str, venue_id: str | None = None):
    client = _venue_staff_client(access_token)
    query = client.table("venue_block").select("*")
    if venue_id:
        query = query.eq("venue_id", venue_id)
    response = query.execute()
    return response.data or []


def create_venue_block(access_token: str, payload: dict) -> dict:
    venue_id = str(payload.get("venue_id", "")).strip()
    blocked_date = str(payload.get("date", "")).strip()
    start_time = str(payload.get("start_time", "")).strip()
    end_time = str(payload.get("end_time", "")).strip()
    reason = str(payload.get("reason", "")).strip() or None

    if not venue_id:
        raise VenueAvailabilityValidationError("venue_id is required.")
    if not blocked_date:
        raise VenueAvailabilityValidationError("date is required.")
    if not start_time:
        raise VenueAvailabilityValidationError("start_time is required.")
    if not end_time:
        raise VenueAvailabilityValidationError("end_time is required.")
    if start_time >= end_time:
        raise VenueAvailabilityValidationError(
            "end_time must be after start_time."
        )

    client = _venue_staff_client(access_token)

    confirmed = (
        client.table("venue_booking")
        .select("*")
        .eq("venue_id", venue_id)
        .eq("requested_date", blocked_date)
        .eq("status", CONFIRMED_STATUS)
        .execute()
    ).data or []

    for booking in confirmed:
        booking_start = booking.get("start_time")
        booking_end = booking.get("end_time")
        if (
            booking_start
            and booking_end
            and start_time < booking_end
            and end_time > booking_start
        ):
            raise VenueAvailabilityOverlapError(
                "Block overlaps a confirmed booking "
                f"({booking.get('id')})."
            )

    insert_payload = {
        "venue_id": venue_id,
        "date": blocked_date,
        "start_time": start_time,
        "end_time": end_time,
        "status": BLOCK_STATUS,
    }
    if reason:
        insert_payload["reason"] = reason

    response = client.table("venue_block").insert(insert_payload).execute()

    if not response.data:
        raise VenueAvailabilityValidationError(
            "Unable to create venue block."
        )

    return response.data[0]
