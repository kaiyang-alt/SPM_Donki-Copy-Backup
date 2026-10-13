from datetime import datetime, timedelta
from itertools import product

from app.supabase_client import create_authenticated_supabase_client


class VenueSearchError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def search_venues(access_token, criteria):
    start = _datetime(criteria.get('start'), 'Start date and time')
    end = _datetime(criteria.get('end'), 'End date and time')
    if end <= start:
        raise VenueSearchError('End date and time must be after the start date and time.')
    setup_minutes = _whole_number(criteria.get('setup_minutes', 0), 'Setup time', minimum=0)
    turnaround_minutes = _whole_number(
        criteria.get('turnaround_minutes', 0), 'Turnaround time', minimum=0
    )
    occupied_start = start - timedelta(minutes=setup_minutes)
    occupied_end = end + timedelta(minutes=turnaround_minutes)
    requirements = _requirements(criteria)

    try:
        client = create_authenticated_supabase_client(access_token)
        user = client.auth.get_user(access_token).user
        if not user:
            raise ValueError('No user')
        role = (client.table('user_role').select('role').eq('user_id', user.id)
                .eq('role', 'event_coordinator').limit(1).execute().data)
        if not role:
            raise VenueSearchError('Event Coordinator access is required.', 403)
        venues = client.table('venue').select('*').eq('active', True).execute().data or []
        if not venues:
            return []
        bookings = (client.table('venue_booking').select('venue_id')
                    .eq('status', 'confirmed')
                    .lt('requested_start', occupied_end.isoformat())
                    .gt('requested_end', occupied_start.isoformat()).execute().data or [])
        blocks = (client.table('venue_block')
                  .select('venue_id,start_datetime,end_datetime,reason,status')
                  .eq('status', 'active').lt('start_datetime', occupied_end.isoformat())
                  .gt('end_datetime', occupied_start.isoformat()).execute().data or [])
    except VenueSearchError:
        raise
    except Exception as exc:
        raise VenueSearchError('Unable to search venues.', 502) from exc

    unavailable = {row['venue_id'] for row in bookings + blocks}
    candidates = [
        [_venue_result(venue, requirement, start, end, occupied_start, occupied_end,
                       setup_minutes, turnaround_minutes)
         for venue in venues
         if venue.get('venue_id') not in unavailable
         and _matches(venue, requirement)]
        for requirement in requirements
    ]
    if len(requirements) == 1:
        return candidates[0]

    combinations = []
    seen = set()
    for selection in product(*candidates):
        venue_ids = [venue['venue_id'] for venue in selection]
        if len(set(venue_ids)) != len(venue_ids):
            continue
        identity = tuple(sorted(venue_ids))
        if identity in seen:
            continue
        seen.add(identity)
        combinations.append({
            'venues': list(selection),
            'event_start': start.isoformat(), 'event_end': end.isoformat(),
            'occupied_start': occupied_start.isoformat(),
            'occupied_end': occupied_end.isoformat(),
            'setup_minutes': setup_minutes,
            'turnaround_minutes': turnaround_minutes,
            'temporary_unavailability': [],
        })
    return combinations


def _requirements(criteria):
    supplied = criteria.get('venue_requirements')
    if supplied is None:
        supplied = [{
            'guest_count': criteria.get('guest_count'),
            'layout': criteria.get('layout'),
            'facilities': criteria.get('facilities'),
        }]
    if not isinstance(supplied, list) or not supplied:
        raise VenueSearchError('At least one venue requirement is required.')
    count = _whole_number(criteria.get('venue_count', len(supplied)),
                          'Number of venues', minimum=1)
    if len(supplied) != count:
        raise VenueSearchError('Provide requirements for every required venue.')
    return [_requirement(item) for item in supplied]


def _requirement(value):
    if not isinstance(value, dict):
        raise VenueSearchError('Each venue requirement must be an object.')
    guest_count = _whole_number(value.get('guest_count'), 'Guest count', minimum=1)
    layout = str(value.get('layout') or '').strip()
    facilities = value.get('facilities')
    if not layout:
        raise VenueSearchError('Room layout is required.')
    if (not isinstance(facilities, list) or not facilities
            or any(not str(item).strip() for item in facilities)):
        raise VenueSearchError('At least one required facility is required.')
    return {
        'guest_count': guest_count,
        'layout': layout,
        'facilities': [str(item).strip() for item in facilities],
    }


def _whole_number(value, label, minimum):
    message = (f'{label} must be a positive whole number.' if minimum == 1
               else f'{label} must be a whole number of at least {minimum}.')
    if isinstance(value, bool):
        raise VenueSearchError(message)
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise VenueSearchError(message) from exc
    if number < minimum or str(value).strip() not in {str(number), f'{number}.0'}:
        raise VenueSearchError(message)
    return number


def _matches(venue, requirement):
    capacity = _layout_capacity(venue, requirement['layout'])
    requested = {_normalise(item) for item in requirement['facilities']}
    return (capacity is not None and capacity >= requirement['guest_count']
            and requested <= _values(venue.get('facilities')))


def _venue_result(venue, requirement, start, end, occupied_start, occupied_end,
                  setup_minutes, turnaround_minutes):
    return {
        'venue_id': venue.get('venue_id'), 'name': venue.get('name'),
        'location': venue.get('location'), 'layout': requirement['layout'],
        'layout_capacity': _layout_capacity(venue, requirement['layout']),
        'facilities': sorted(_values(venue.get('facilities'))),
        'available_start': start.isoformat(), 'available_end': end.isoformat(),
        'event_start': start.isoformat(), 'event_end': end.isoformat(),
        'occupied_start': occupied_start.isoformat(),
        'occupied_end': occupied_end.isoformat(),
        'setup_minutes': setup_minutes,
        'turnaround_minutes': turnaround_minutes,
        'temporary_unavailability': [],
    }


def _datetime(value, label):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('Timezone required')
        return parsed
    except (TypeError, ValueError) as exc:
        raise VenueSearchError(f'{label} is required and must include a timezone.') from exc


def _normalise(value):
    return ' '.join(str(value).strip().casefold().split())


def _values(value):
    if isinstance(value, list):
        return {_normalise(item) for item in value}
    if isinstance(value, dict):
        return {_normalise(key) for key, enabled in value.items() if enabled}
    return set()


def _layout_capacity(venue, requested_layout):
    layouts = venue.get('supported_layouts')
    wanted = _normalise(requested_layout)
    if isinstance(layouts, list):
        return venue.get('capacity') if wanted in {_normalise(item) for item in layouts} else None
    if isinstance(layouts, dict):
        for name, specification in layouts.items():
            if _normalise(name) != wanted or specification is False or specification is None:
                continue
            if isinstance(specification, dict):
                return specification.get('capacity', venue.get('capacity'))
            if isinstance(specification, (int, float)) and not isinstance(specification, bool):
                return specification
            return venue.get('capacity')
    return None
