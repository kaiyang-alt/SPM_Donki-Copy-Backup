from app.supabase_client import supabase
class EventNotFoundError(Exception):
    pass

class EventNotEditableError(Exception):
    pass
def get_event_details_for_organiser(event_id: str, organiser_id: str):
    """
    Fetches event details and related arrangements for an organiser.
    Enforces ownership authorization and compiles outstanding items.
    """
    # Query event with joined venue_booking (and venue) and equipment_reservation
    response = (
        supabase.table("event")
        .select("*, venue_booking(*, venue(*)), equipment_reservation(*, equipment(*))")
        .eq("event_id", event_id)
        .execute()
    )

    if not response.data:
        return None, "EVENT_NOT_FOUND"

    event = response.data[0]

    # Acceptance Criteria: Denied access when attempting to view un-owned event
    if str(event.get("organiser_id")) != str(organiser_id):
        return None, "UNAUTHORIZED"

    # Map status display labels & identify outstanding arrangements
    outstanding_arrangements = []

    # Check Venue Bookings
    venue_bookings = event.get("venue_booking", [])
    for booking in venue_bookings:
        status = booking.get("status")
        if status in ["requested", "tentative"]:
            outstanding_arrangements.append(f"Venue Booking: Pending Approval ({status})")
        elif status in ["rejected", "cancelled"]:
            outstanding_arrangements.append(f"Venue Booking: Unfulfilled ({status})")

    if not venue_bookings:
        outstanding_arrangements.append("Venue Booking: No booking requested yet")

    # Check Equipment/Technical Support Reservations
    equipment_reservations = event.get("equipment_reservation", [])
    if event.get("technical_support_required"):
        for res in equipment_reservations:
            status = res.get("status")
            eq_name = res.get("equipment", {}).get("name", "Equipment") if res.get("equipment") else "Equipment"
            if status == "requested":
                outstanding_arrangements.append(f"Tech/Equipment ({eq_name}): Pending Reservation")
            elif status in ["rejected", "cancelled"]:
                outstanding_arrangements.append(f"Tech/Equipment ({eq_name}): {status.capitalize()}")
        
        if not equipment_reservations:
            outstanding_arrangements.append("Tech Support: Required but no equipment reserved")

    event["outstanding_arrangements"] = outstanding_arrangements
    return event, None
