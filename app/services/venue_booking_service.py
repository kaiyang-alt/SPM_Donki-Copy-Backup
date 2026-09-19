from datetime import date, time
import logging
import re

from app.supabase_client import create_authenticated_supabase_client

logger = logging.getLogger(__name__)


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
    roles = client.table('user_role').select('role').eq('user_id', user_id).eq('role', role).execute()
    if not roles.data:
        raise VenueBookingError("You do not have permission to perform this action.", 403)
    return client, user_id


def validate_booking_payload(payload):
    """Validate and normalise submission data before accessing the database."""
    if not isinstance(payload, dict):
        raise VenueBookingError("Request body must be a JSON object.")
    required = ('event_id', 'venue_id', 'booking_date', 'start_time', 'end_time', 'setup_layout')
    cleaned = {}
    for field in required:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise VenueBookingError(f"{field} must be a non-empty string.")
        cleaned[field] = value.strip()
    validate_time_slot(cleaned['booking_date'], cleaned['start_time'], cleaned['end_time'])
    notes = payload.get('setup_notes')
    if notes is not None and not isinstance(notes, str):
        raise VenueBookingError("setup_notes must be a string.")
    cleaned['setup_notes'] = (notes.strip() or None) if notes is not None else None
    return cleaned


def validate_time_slot(slot_date, start_time, end_time):
    try:
        if not isinstance(slot_date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', slot_date):
            raise ValueError()
        date.fromisoformat(slot_date)
        for value in (start_time, end_time):
            if not isinstance(value, str) or not re.fullmatch(r'\d{2}:\d{2}(:\d{2})?', value):
                raise ValueError()
        start, end = time.fromisoformat(start_time), time.fromisoformat(end_time)
    except ValueError as exc:
        raise VenueBookingError("Use a valid date (YYYY-MM-DD) and time (HH:MM or HH:MM:SS).") from exc
    if start >= end:
        raise VenueBookingError("End time must be after start time on the same date.")

def execute_conflict_check(supabase, venue_id, booking_date, start_time, end_time, exclude_booking_id=None):
    """
    Checks for overlapping bookings or blackout dates in venue_booking and venue_block.
    """
    # Check existing active/pending bookings for schedule collisions
    query = supabase.table('venue_booking') \
        .select('id') \
        .eq('venue_id', venue_id) \
        .eq('booking_date', booking_date) \
        .in_('status', ['requested', 'tentative', 'confirmed']) \
        .lt('start_time', end_time) \
        .gt('end_time', start_time)

    if exclude_booking_id:
        query = query.neq('id', exclude_booking_id)

    booking_conflict = query.execute()
    if booking_conflict.data:
        return True

    # Check blackout periods in venue_block
    block_conflict = supabase.table('venue_block') \
        .select('id') \
        .eq('venue_id', venue_id) \
        .eq('block_date', booking_date) \
        .lt('start_time', end_time) \
        .gt('end_time', start_time) \
        .execute()

    if block_conflict.data:
        return True

    return False


def submit_venue_booking_request(access_token, event_id, venue_id, booking_date, start_time, end_time, setup_layout, setup_notes=None):
    """Submits a new venue booking request with status 'requested'."""
    booking_payload = validate_booking_payload({
        'event_id': event_id, 'venue_id': venue_id, 'booking_date': booking_date,
        'start_time': start_time, 'end_time': end_time,
        'setup_layout': setup_layout, 'setup_notes': setup_notes,
    })
    event_id = booking_payload['event_id']
    venue_id = booking_payload['venue_id']
    booking_date = booking_payload['booking_date']
    start_time = booking_payload['start_time']
    end_time = booking_payload['end_time']
    supabase, user_id = authenticated_venue_client(access_token, 'event_coordinator')

    event_res = supabase.table('event').select('*').eq('event_id', event_id).execute()
    if not event_res.data:
        return {"success": False, "error": "Event not found."}, 404

    event = event_res.data[0]
    if event.get('status') != 'planning':
        return {
            "success": False,
            "error": "Venue bookings can only be requested for approved events in planning status."
        }, 400

    existing = (supabase.table('venue_booking').select('*')
                .eq('event_id', event_id)
                .in_('status', ['requested', 'tentative', 'confirmed']).execute())
    if existing.data:
        return {"success": False, "error": "This event already has an active venue arrangement."}, 409

    if execute_conflict_check(supabase, venue_id, booking_date, start_time, end_time):
        return {
            "success": False,
            "error": "The selected venue slot is unavailable due to an existing booking or blackout period."
        }, 409

    booking_payload['status'] = 'requested'

    booking_res = supabase.table('venue_booking').insert(booking_payload).execute()
    if not booking_res.data:
        return {"success": False, "error": "Failed to create venue booking request."}, 500

    created_booking = booking_res.data[0]

    # The current recipient lookup is provisional until the venue/staff assignment
    # relationship is supplied. See the story's integration blockers.
    notification_sent = False
    try:
        staff_res = supabase.table('user_role').select('user_id').eq('role', 'venue_staff').execute()
        if staff_res.data:
            notifications = [
                {
                    "user_id": staff['user_id'],
                    "title": "New Venue Booking Request",
                    "message": f"New booking request (ID: {created_booking['id']}) for Venue {venue_id} requires review.",
                    "is_read": False
                }
                for staff in staff_res.data
            ]
            result = supabase.table('notification').insert(notifications).execute()
            notification_sent = bool(result.data)
    except Exception:
        logger.exception('Booking saved, but venue notification delivery failed.')

    response = {
        "success": True,
        "message": "Venue booking request submitted successfully.",
        "booking": created_booking,
        "display_status": "Pending Venue Approval",
        "notification_sent": notification_sent,
    }
    if not notification_sent:
        response['warning'] = "Booking saved, but Venue Staff notification could not be confirmed. Do not resubmit the booking."
    return response, 201


def get_all_booking_requests(access_token):
    """Retrieves all venue booking requests formatted with venue details, event capacity, and overlaps."""
    supabase, _ = authenticated_venue_client(access_token, 'venue_staff')
    bookings_res = supabase.table('venue_booking').select('*, venue(*), event(*)').execute()
    
    requests_list = []
    for b in bookings_res.data or []:
        venue = b.get('venue') or {}
        event = b.get('event') or {}
        
        # Check for overlapping holds/bookings
        has_overlap = execute_conflict_check(
            supabase, b['venue_id'], b['booking_date'], b['start_time'], b['end_time'], exclude_booking_id=b['id']
        )

        requests_list.append({
            "booking_id": b['id'],
            "status": b['status'],
            "requested_date": b['booking_date'],
            "time_slot": f"{b['start_time']} - {b['end_time']}",
            "setup_layout": b.get('setup_layout'),
            "setup_notes": b.get('setup_notes'),
            "event_capacity_required": event.get('expected_capacity', 0),
            "venue_listed_capacity": venue.get('capacity', 0),
            "venue_layout": venue.get('layout_type'),
            "venue_accessibility": venue.get('accessibility_info'),
            "has_overlapping_conflict": has_overlap,
            "rejection_reason": b.get('rejection_reason'),
            "suggested_alternatives": b.get('suggested_alternatives')
        })

    return {"success": True, "requests": requests_list}, 200


def approve_venue_booking_request(access_token, booking_id):
    """Approves a booking request using first-come, first-served conflict enforcement."""
    supabase, _ = authenticated_venue_client(access_token, 'venue_staff')

    booking_res = supabase.table('venue_booking').select('*').eq('id', booking_id).execute()
    if not booking_res.data:
        return {"success": False, "error": "Booking request not found."}, 404

    booking = booking_res.data[0]
    if booking['status'] == 'rejected':
        return {"success": False, "error": "Cannot approve a permanently rejected request."}, 400
    if booking['status'] not in ('requested', 'tentative'):
        return {"success": False, "error": "Only pending requests can be approved."}, 409

    if execute_conflict_check(supabase, booking['venue_id'], booking['booking_date'], booking['start_time'], booking['end_time'], exclude_booking_id=booking_id):
        return {"success": False, "error": "Cannot approve. Time slot was claimed by a prior request."}, 409

    updated_res = (supabase.table('venue_booking').update({"status": "confirmed"})
                   .eq('id', booking_id).eq('status', booking['status']).execute())
    if not updated_res.data:
        return {"success": False, "error": "The booking changed. Refresh before trying again."}, 409

    # Notify Event Coordinator
    event_res = supabase.table('event').select('coordinator_id').eq('event_id', booking['event_id']).execute()
    if event_res.data and event_res.data[0].get('coordinator_id'):
        supabase.table('notification').insert({
            "user_id": event_res.data[0]['coordinator_id'],
            "title": "Booking Request Approved",
            "message": f"Your booking request for Venue {booking['venue_id']} has been approved.",
            "is_read": False
        }).execute()

    return {"success": True, "message": "Booking request approved.", "booking": updated_res.data[0]}, 200


def reject_venue_booking_request(access_token, booking_id, reason=None, alternative_venue_ids=None):
    """Rejects a booking request with optional notes and suggested alternatives. Immutable status."""
    if reason is not None and not isinstance(reason, str):
        raise VenueBookingError("reason must be a string.")
    if alternative_venue_ids is not None and (
        not isinstance(alternative_venue_ids, list)
        or any(not isinstance(value, str) or not value.strip() for value in alternative_venue_ids)
    ):
        raise VenueBookingError("alternative_venue_ids must be a list of venue IDs.")
    supabase, _ = authenticated_venue_client(access_token, 'venue_staff')

    booking_res = supabase.table('venue_booking').select('*').eq('id', booking_id).execute()
    if not booking_res.data:
        return {"success": False, "error": "Booking request not found."}, 404

    booking = booking_res.data[0]
    if booking['status'] == 'rejected':
        return {"success": False, "error": "Request is already rejected and cannot be modified."}, 400
    if booking['status'] not in ('requested', 'tentative'):
        return {"success": False, "error": "Only pending requests can be rejected."}, 409

    update_payload = {
        "status": "rejected",
        "rejection_reason": reason,
        "suggested_alternatives": alternative_venue_ids or []
    }

    updated_res = (supabase.table('venue_booking').update(update_payload)
                   .eq('id', booking_id).eq('status', booking['status']).execute())
    if not updated_res.data:
        return {"success": False, "error": "The booking changed. Refresh before trying again."}, 409

    # Notify Event Coordinator
    event_res = supabase.table('event').select('coordinator_id').eq('event_id', booking['event_id']).execute()
    if event_res.data and event_res.data[0].get('coordinator_id'):
        supabase.table('notification').insert({
            "user_id": event_res.data[0]['coordinator_id'],
            "title": "Booking Request Rejected",
            "message": f"Your booking request for Venue {booking['venue_id']} was rejected. Reason: {reason or 'N/A'}",
            "is_read": False
        }).execute()

    return {
        "success": True,
        "message": "Booking request rejected.",
        "booking": updated_res.data[0]
    }, 200


def block_venue_availability(access_token, venue_id, block_date, start_time, end_time, reason=None):
    """Marks a venue slot as unavailable without altering existing confirmed bookings."""
    validate_time_slot(block_date, start_time, end_time)
    if reason is not None and not isinstance(reason, str):
        raise VenueBookingError("reason must be a string.")
    supabase, _ = authenticated_venue_client(access_token, 'venue_staff')

    payload = {
        "venue_id": venue_id,
        "block_date": block_date,
        "start_time": start_time,
        "end_time": end_time,
        "reason": reason
    }

    res = supabase.table('venue_block').insert(payload).execute()
    if not res.data:
        return {"success": False, "error": "Failed to create venue blackout block."}, 500

    return {"success": True, "message": "Venue block created successfully.", "block": res.data[0]}, 201


def update_venue_details(access_token, venue_id, capacity=None, layout_type=None, accessibility_info=None):
    """Updates venue specifications (capacity, layout, accessibility)."""
    if capacity is not None and (type(capacity) is not int or capacity <= 0):
        raise VenueBookingError("capacity must be a positive integer.")
    for field, value in [('layout_type', layout_type), ('accessibility_info', accessibility_info)]:
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise VenueBookingError(f"{field} must be a non-empty string.")
    if all(value is None for value in (capacity, layout_type, accessibility_info)):
        raise VenueBookingError("Provide at least one venue detail to update.")
    supabase, _ = authenticated_venue_client(access_token, 'venue_staff')
    payload = {}
    if capacity is not None: payload['capacity'] = capacity
    if layout_type is not None: payload['layout_type'] = layout_type
    if accessibility_info is not None: payload['accessibility_info'] = accessibility_info

    res = supabase.table('venue').update(payload).eq('id', venue_id).execute()
    if not res.data:
        return {"success": False, "error": "Failed to update venue details."}, 400

    return {"success": True, "message": "Venue details updated.", "venue": res.data[0]}, 200


def get_venue_schedule(access_token, venue_id):
    """Retrieves unified calendar schedule of bookings, holds, and blackout blocks."""
    supabase, _ = authenticated_venue_client(access_token, 'venue_staff')
    bookings = supabase.table('venue_booking').select('*').eq('venue_id', venue_id).execute()
    blocks = supabase.table('venue_block').select('*').eq('venue_id', venue_id).execute()

    return {
        "success": True,
        "schedule": {
            "bookings_and_holds": bookings.data or [],
            "maintenance_blocks": blocks.data or []
        }
    }, 200
