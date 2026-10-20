from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.exceptions import HTTPException
from app.services.venue_buffer_service import read_buffer_notifications, read_venue_buffers, save_venue_buffers
from app.services.venue_occupancy import VenueOccupancyError
from app.services.venue_booking_service import (
    VenueBookingError,
    validate_booking_payload,
    validate_time_slot,
    submit_venue_booking_request,
    get_coordinator_booking_context,
    list_available_venues,
    get_all_booking_requests,
    get_venue_staff_context,
    approve_venue_booking_request,
    reject_venue_booking_request,
    block_venue_availability,
    update_venue_details,
    get_venue_schedule
)

venue_booking_bp = Blueprint('venue_booking', __name__)


@venue_booking_bp.before_request
def require_authentication():
    scheme, _, token = request.headers.get('Authorization', '').partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        return jsonify(success=False, error='Authentication is required.'), 401
    g.venue_access_token = token.strip()


@venue_booking_bp.errorhandler(VenueBookingError)
@venue_booking_bp.errorhandler(VenueOccupancyError)
def handle_booking_error(error):
    body = {"success": False, "error": str(error)}
    if getattr(error, 'code', None):
        body['code'] = error.code
    return jsonify(body), error.status_code


@venue_booking_bp.errorhandler(Exception)
def handle_database_error(error):
    if isinstance(error, HTTPException):
        return jsonify(success=False, error=error.description), error.code
    # Honour existing database uniqueness/exclusion constraints if configured.
    if getattr(error, 'code', None) in ('23505', '23P01'):
        return jsonify(success=False, error='The venue arrangement conflicts with an existing record.'), 409
    current_app.logger.exception('Venue booking operation failed.')
    return jsonify(success=False, error='Unable to complete the venue operation.'), 503


def json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise VenueBookingError('Request body must be a JSON object.')
    return data


@venue_booking_bp.get('/api/venues/<venue_id>/buffers')
def handle_read_venue_buffers(venue_id):
    return jsonify(read_venue_buffers(g.venue_access_token, venue_id)), 200


@venue_booking_bp.get('/api/venue-buffer-notifications')
def handle_buffer_notifications():
    return jsonify(read_buffer_notifications(g.venue_access_token)), 200


@venue_booking_bp.put('/api/venues/<venue_id>/buffers')
def handle_save_venue_buffers(venue_id):
    return jsonify(save_venue_buffers(g.venue_access_token, venue_id, json_object())), 200


@venue_booking_bp.route('/api/venue-bookings', methods=['POST'])
def handle_submit_venue_booking():
    """POST /api/venue-bookings - Submit request"""
    data = validate_booking_payload(json_object())

    result, status_code = submit_venue_booking_request(
        access_token=g.venue_access_token,
        event_id=data['event_id'],
        venue_id=data['venue_id'],
        booking_date=data['booking_date'],
        start_time=data['start_time'],
        end_time=data['end_time'],
        setup_layout=data['setup_layout']
    )
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venue-bookings/context', methods=['GET'])
def handle_coordinator_booking_context():
    """GET booking form data and persisted status for the signed-in Coordinator."""
    result, status_code = get_coordinator_booking_context(g.venue_access_token)
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venue-bookings/availability', methods=['POST'])
def handle_available_venues():
    """Return venues eligible and conflict-free for the requested arrangement."""
    data = validate_booking_payload(json_object(), require_venue=False)
    result, status_code = list_available_venues(
        access_token=g.venue_access_token,
        event_id=data['event_id'],
        booking_date=data['booking_date'],
        start_time=data['start_time'],
        end_time=data['end_time'],
        setup_layout=data['setup_layout'],
    )
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venue-bookings', methods=['GET'])
def handle_get_booking_requests():
    """GET /api/venue-bookings - Review incoming requests"""
    result, status_code = get_all_booking_requests(g.venue_access_token)
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venue-staff/context', methods=['GET'])
def handle_venue_staff_context():
    result, status_code = get_venue_staff_context(g.venue_access_token)
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venue-bookings/<booking_id>/approve', methods=['POST'])
def handle_approve_request(booking_id):
    """POST /api/venue-bookings/<id>/approve - Approve request"""
    result, status_code = approve_venue_booking_request(g.venue_access_token, booking_id)
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venue-bookings/<booking_id>/reject', methods=['POST'])
def handle_reject_request(booking_id):
    """POST /api/venue-bookings/<id>/reject - Reject request with optional note & alternatives"""
    data = json_object()
    result, status_code = reject_venue_booking_request(
        access_token=g.venue_access_token,
        booking_id=booking_id,
        reason=data.get('reason'),
        alternative_venue_ids=data.get('alternative_venue_ids')
    )
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venues/<venue_id>/block', methods=['POST'])
def handle_block_venue(venue_id):
    """POST /api/venues/<id>/block - Mark slot as unavailable"""
    data = json_object()
    required = ['block_date', 'start_time', 'end_time']
    missing = [f for f in required if not data.get(f)]

    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

    validate_time_slot(data['block_date'], data['start_time'], data['end_time'])

    result, status_code = block_venue_availability(
        access_token=g.venue_access_token,
        venue_id=venue_id,
        block_date=data['block_date'],
        start_time=data['start_time'],
        end_time=data['end_time'],
        reason=data.get('reason')
    )
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venues/<venue_id>', methods=['PUT'])
def handle_update_venue(venue_id):
    """PUT /api/venues/<id> - Update capacity, layout, accessibility"""
    data = json_object()
    result, status_code = update_venue_details(
        access_token=g.venue_access_token,
        venue_id=venue_id,
        capacity=data.get('capacity'),
        supported_layouts=data.get('supported_layouts'),
        accessibility=data.get('accessibility')
    )
    return jsonify(result), status_code


@venue_booking_bp.route('/api/venues/<venue_id>/schedule', methods=['GET'])
def handle_get_venue_schedule(venue_id):
    """GET /api/venues/<id>/schedule - Get calendar view of holds/blocks"""
    result, status_code = get_venue_schedule(g.venue_access_token, venue_id)
    return jsonify(result), status_code
