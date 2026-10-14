from app.supabase_client import create_authenticated_supabase_client

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"


class VenueAccessError(Exception):
    """Raised when the authenticated user lacks Venue Staff access."""


class BookingRequestNotFoundError(Exception):
    pass


class InvalidStatusError(Exception):
    pass


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
        raise VenueAccessError("Venue Staff access required.")
    return client


def list_venue_booking_requests(access_token: str, venue_id: str | None = None):
    client = _venue_staff_client(access_token)
    query = client.table("venue_booking").select("*")
    if venue_id:
        query = query.eq("venue_id", venue_id)
    response = query.order("created_at", desc=False).execute()
    return response.data or []


def update_venue_booking_request_status(
    access_token: str, request_id: str, new_status: str
):
    normalised = (new_status or "").strip().lower()
    if normalised not in {APPROVED, REJECTED}:
        raise InvalidStatusError(
            "Invalid status. Must be 'approved' or 'rejected'."
        )

    client = _venue_staff_client(access_token)

    res = (
        client.table("venue_booking")
        .select("*")
        .eq("id", request_id)
        .execute()
    )
    if not res.data:
        raise BookingRequestNotFoundError(
            f"Booking request {request_id} not found."
        )

    current = res.data[0]
    warning = None

    if normalised == APPROVED:
        overlaps = (
            client.table("venue_booking")
            .select("*")
            .eq("venue_id", current.get("venue_id"))
            .eq("requested_date", current.get("requested_date"))
            .eq("status", PENDING)
            .neq("id", request_id)
            .execute()
        )
        conflicting = [
            r for r in (overlaps.data or [])
            if current.get("start_time") < r.get("end_time")
            and current.get("end_time") > r.get("start_time")
        ]
        if conflicting:
            warning = {
                "message": (
                    f"Approval creates schedule conflict with "
                    f"{len(conflicting)} remaining pending request(s)."
                ),
                "conflicting_request_ids": [r["id"] for r in conflicting],
            }

    update_res = (
        client.table("venue_booking")
        .update({"status": normalised})
        .eq("id", request_id)
        .execute()
    )
    return (update_res.data[0] if update_res.data else current), warning