from datetime import datetime

from app.supabase_client import create_authenticated_supabase_client
from app.services.venue_occupancy import (
    VenueOccupancyError, assess_candidate, caller_has_complete_venue_reads,
    configuration,
    load_occupancy_rows,
)


class VenueSearchError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class VenueSearchResults(list):
    """Keep the existing list contract and expose incomplete assessments to UI."""
    def __init__(self):
        super().__init__()
        self.assessment_limitations = []


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
            return VenueSearchResults()
        # No raw-time prefilter: it would discard buffer-only conflicts.
        bookings, bookings_complete = load_occupancy_rows(client, 'venue_booking')
        blocks, blocks_complete = load_occupancy_rows(client, 'venue_block')
        source_complete = bookings_complete and blocks_complete and caller_has_complete_venue_reads(client, user.id)
    except VenueSearchError:
        raise
    except Exception as exc:
        raise VenueSearchError('Unable to search venues.', 502) from exc

    requested = {_normalise(item) for item in facilities}
    results = VenueSearchResults()
    for venue in venues:
        layout_capacity = _layout_capacity(venue, layout)
        available_facilities = _values(venue.get('facilities'))
        if (layout_capacity is not None and layout_capacity >= guest_count and requested <= available_facilities):
            try:
                assessment = assess_candidate(
                    venue, [row for row in bookings if row.get('venue_id') == venue['venue_id']],
                    [row for row in blocks if row.get('venue_id') == venue['venue_id']],
                    start, end, source_complete,
                )
            except VenueOccupancyError as exc:
                results.assessment_limitations.append({'venue_id': venue['venue_id'], 'code': exc.code, 'reason': str(exc)})
                continue
            if not assessment['assessment_complete']:
                results.assessment_limitations.append({
                    'venue_id': venue['venue_id'], 'limitations': assessment['assessment_limitations'],
                    'blockers': assessment['assessment_blockers'],
                    'potential_conflicts': assessment['candidate_conflicts'],
                })
            if not assessment['available']:
                continue
            results.append({
                **configuration(venue),
                'venue_id': venue.get('venue_id'), 'name': venue.get('name'),
                'location': venue.get('location'), 'layout': layout,
                'layout_capacity': layout_capacity,
                'facilities': sorted(available_facilities),
                'available_start': start.isoformat(), 'available_end': end.isoformat(),
                'occupied_start': assessment['occupied_start'], 'occupied_end': assessment['occupied_end'],
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
