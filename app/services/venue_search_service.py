from datetime import datetime

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
    try:
        guest_count = int(criteria.get('guest_count'))
    except (TypeError, ValueError) as exc:
        raise VenueSearchError('Guest count must be a positive whole number.') from exc
    if guest_count < 1:
        raise VenueSearchError('Guest count must be a positive whole number.')
    layout = str(criteria.get('layout') or '').strip()
    facilities = criteria.get('facilities')
    if not layout:
        raise VenueSearchError('Room layout is required.')
    if not isinstance(facilities, list) or not facilities or any(not str(item).strip() for item in facilities):
        raise VenueSearchError('At least one required facility is required.')

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
                    .eq('status', 'confirmed').lt('requested_start', end.isoformat())
                    .gt('requested_end', start.isoformat()).execute().data or [])
        blocks = (client.table('venue_block').select('venue_id')
                  .eq('status', 'active').lt('start_datetime', end.isoformat())
                  .gt('end_datetime', start.isoformat()).execute().data or [])
    except VenueSearchError:
        raise
    except Exception as exc:
        raise VenueSearchError('Unable to search venues.', 502) from exc

    unavailable = {row['venue_id'] for row in bookings + blocks}
    requested = {_normalise(item) for item in facilities}
    results = []
    for venue in venues:
        layout_capacity = _layout_capacity(venue, layout)
        available_facilities = _values(venue.get('facilities'))
        if (venue.get('venue_id') not in unavailable and layout_capacity is not None
                and layout_capacity >= guest_count and requested <= available_facilities):
            results.append({
                'venue_id': venue.get('venue_id'), 'name': venue.get('name'),
                'location': venue.get('location'), 'layout': layout,
                'layout_capacity': layout_capacity,
                'facilities': sorted(available_facilities),
                'available_start': start.isoformat(), 'available_end': end.isoformat(),
            })
    return results


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
