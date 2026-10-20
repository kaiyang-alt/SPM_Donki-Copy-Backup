from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.venue_search_service import VenueSearchError, _layout_capacity, search_venues


CRITERIA = {
    'start': '2026-11-20T01:00:00+00:00',
    'end': '2026-11-20T09:00:00+00:00',
    'guest_count': 150, 'layout': 'Theatre',
    'facilities': ['Projector', 'Sound system'],
}


def _client(venues, bookings=None, blocks=None):
    # Explicit fixture values, not application defaults or live population.
    venues = [{"setup_minutes": 15, "turnaround_minutes": 15, "buffer_config_revision": 0, **venue} for venue in venues]
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id='coordinator-1'))
    tables = {name: MagicMock() for name in ['user_role', 'venue', 'venue_booking', 'venue_block']}
    client.table.side_effect = tables.__getitem__
    role_query = tables['user_role'].select.return_value
    role_query.eq.return_value = role_query
    role_query.limit.return_value = role_query
    role_query.execute.return_value.data = [{'role': 'event_coordinator'}]
    tables['venue'].select.return_value.eq.return_value.execute.return_value.data = venues
    for name, rows in [('venue_booking', bookings or []), ('venue_block', blocks or [])]:
        query = tables[name].select.return_value
        query.eq.return_value = query
        query.lt.return_value = query
        query.gt.return_value = query
        query.execute.return_value.data = rows
        query.execute.return_value.count = len(rows)
    return client, tables


@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_search_matches_every_requirement_and_excludes_conflicts(create_client):
    venues = [
        {'venue_id': 'alcove', 'name': 'The Alcove', 'location': 'A', 'capacity': 180,
         'facilities': ['Projector', 'Sound system'], 'supported_layouts': ['Theatre']},
        {'venue_id': 'small', 'name': 'Small Room', 'capacity': 120,
         'facilities': ['Projector', 'Sound system'], 'supported_layouts': ['Theatre']},
        {'venue_id': 'missing', 'name': 'Campus Green', 'capacity': 300,
         'facilities': ['Sound system'], 'supported_layouts': ['Theatre']},
        {'venue_id': 'booked', 'name': 'Booked Hall', 'capacity': 300,
         'facilities': ['Projector', 'Sound system'], 'supported_layouts': ['Theatre']},
        {'venue_id': 'blocked', 'name': 'Closed Hall', 'capacity': 300,
         'facilities': ['Projector', 'Sound system'], 'supported_layouts': ['Theatre']},
    ]
    client, tables = _client(venues, [{'venue_id': 'booked'}], [{'venue_id': 'blocked'}])
    create_client.return_value = client
    results = search_venues('token', CRITERIA)
    assert [venue['venue_id'] for venue in results] == ['alcove']
    assert results[0]['layout_capacity'] == 180
    assert results[0]['available_start'] == CRITERIA['start']
    booking_query = tables['venue_booking'].select.return_value
    booking_query.lt.assert_not_called()
    booking_query.gt.assert_not_called()
    block_query = tables['venue_block'].select.return_value
    block_query.lt.assert_not_called()
    block_query.gt.assert_not_called()


def test_layout_capacity_supports_approved_json_column_shapes():
    assert _layout_capacity({'capacity': 180, 'supported_layouts': ['Theatre']}, 'theatre') == 180
    assert _layout_capacity({'capacity': 180, 'supported_layouts': {'Theatre': 150}}, 'theatre') == 150
    assert _layout_capacity({'capacity': 180, 'supported_layouts': {'Theatre': {'capacity': 140}}}, 'theatre') == 140
    assert _layout_capacity({'capacity': 180, 'supported_layouts': ['Classroom']}, 'theatre') is None


@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_search_returns_no_results_when_there_are_no_active_venues(create_client):
    client, tables = _client([])
    create_client.return_value = client

    assert search_venues('token', CRITERIA) == []
    tables['venue_booking'].select.assert_not_called()
    tables['venue_block'].select.assert_not_called()


@pytest.mark.parametrize('change,message', [
    ({'end': '2026-11-20T01:00:00+00:00'}, 'after'),
    ({'guest_count': 0}, 'positive'),
    ({'layout': ''}, 'layout'),
    ({'facilities': []}, 'facility'),
])
def test_invalid_search_criteria_are_rejected_before_database_access(change, message):
    criteria = {**CRITERIA, **change}
    with patch('app.services.venue_search_service.create_authenticated_supabase_client') as create_client:
        with pytest.raises(VenueSearchError, match=message):
            search_venues('token', criteria)
        create_client.assert_not_called()


@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_non_coordinator_cannot_search(create_client):
    client, tables = _client([])
    tables['user_role'].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    create_client.return_value = client
    with pytest.raises(VenueSearchError) as error:
        search_venues('token', CRITERIA)
    assert error.value.status == 403
    tables['venue'].select.assert_not_called()


def test_route_requires_authentication_and_json_object():
    client = app.test_client()
    assert client.post('/api/venues/search', json=CRITERIA).status_code == 401
    assert client.post('/api/venues/search', headers={'Authorization': 'Bearer token'}, json=[]).status_code == 400


@patch('app.routes.venue_search.search_venues')
def test_route_returns_matching_venues(search):
    search.return_value = [{'venue_id': 'alcove', 'name': 'The Alcove'}]
    response = app.test_client().post('/api/venues/search',
        headers={'Authorization': 'Bearer token'}, json=CRITERIA)
    assert response.status_code == 200
    assert response.get_json()['venues'][0]['name'] == 'The Alcove'
    search.assert_called_once_with('token', CRITERIA)


@pytest.mark.parametrize('start,end', [('09:00', '09:15'), ('13:00', '13:30')])
@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_search_detects_setup_and_turnaround_only_conflicts(create_client, start, end):
    venue = {'venue_id': 'hall', 'capacity': 180, 'supported_layouts': ['Theatre'], 'facilities': CRITERIA['facilities'], 'setup_minutes': 30, 'turnaround_minutes': 45}
    booking = {'venue_id': 'hall', 'booking_id': 'reference', 'status': 'confirmed', 'requested_start': '2027-03-10T10:00:00+08:00', 'requested_end': '2027-03-10T12:00:00+08:00'}
    client, _ = _client([venue], [booking])
    create_client.return_value = client
    results = search_venues('token', {**CRITERIA, 'start': f'2027-03-10T{start}:00+08:00', 'end': f'2027-03-10T{end}:00+08:00'})
    assert results == []
    assert results.assessment_limitations == []  # A genuine, assessable conflict.


@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_coordinator_only_complete_empty_reads_allow_availability(create_client):
    venue = {'venue_id': 'hall', 'capacity': 180, 'supported_layouts': ['Theatre'], 'facilities': CRITERIA['facilities']}
    client, tables = _client([venue])
    create_client.return_value = client
    results = search_venues('token', CRITERIA)
    assert [row['venue_id'] for row in results] == ['hall']
    assert results.assessment_limitations == []
    create_client.assert_called_once_with('token')
    tables['venue_booking'].select.assert_called_once_with('*', count='exact')
    tables['venue_block'].select.assert_called_once_with('*', count='exact')


@pytest.mark.parametrize('table', ['venue_booking', 'venue_block'])
@pytest.mark.parametrize('count', [None, 1])
@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_coordinator_only_truncated_or_unverified_read_is_not_available(create_client, table, count):
    venue = {'venue_id': 'hall', 'capacity': 180, 'supported_layouts': ['Theatre'], 'facilities': CRITERIA['facilities']}
    client, tables = _client([venue])
    tables[table].select.return_value.execute.return_value.count = count
    create_client.return_value = client
    results = search_venues('token', CRITERIA)
    assert not results
    assert results.assessment_limitations


@pytest.mark.parametrize('table,record,reason', [
    ('venue_booking', {'booking_id': 'bad', 'status': 'confirmed', 'requested_start': None, 'requested_end': CRITERIA['end']}, 'confirmed_or_expanded_schedule_unassessable'),
    ('venue_booking', {'booking_id': 'bad', 'status': None}, 'booking_lifecycle_classification_required'),
    ('venue_block', {'venue_block_id': 'bad', 'status': 'active', 'start_datetime': CRITERIA['start'], 'end_datetime': None}, 'active_block_interval_unresolved_under_bounded_scope'),
])
@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_coordinator_only_malformed_occupancy_is_not_available(create_client, table, record, reason):
    venue = {'venue_id': 'hall', 'capacity': 180, 'supported_layouts': ['Theatre'], 'facilities': CRITERIA['facilities']}
    row = {'venue_id': 'hall', **record}
    client, _ = _client([venue], [row] if table == 'venue_booking' else [], [row] if table == 'venue_block' else [])
    create_client.return_value = client
    results = search_venues('token', CRITERIA)
    assert not results
    assert results.assessment_limitations[0]['blockers'][0]['reason'] == reason
    assert row == {'venue_id': 'hall', **record}


@pytest.mark.parametrize('status', ['requested', 'tentative'])
@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_hold_not_classified_from_status_alone(create_client, status):
    venue = {'venue_id': 'hall', 'capacity': 180, 'supported_layouts': ['Theatre'], 'facilities': CRITERIA['facilities']}
    hold = {'venue_id': 'hall', 'booking_id': 'hold', 'status': status, 'requested_start': CRITERIA['start'], 'requested_end': CRITERIA['end']}
    client, _ = _client([venue], [hold])
    create_client.return_value = client
    results = search_venues('token', CRITERIA)
    assert not results
    assert results.assessment_limitations[0]['potential_conflicts'][0]['assessment'] == 'potential_hold_validity_unavailable'
    assert hold['status'] == status
