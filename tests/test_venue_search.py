from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.venue_search_service import VenueSearchError, _layout_capacity, search_venues


CRITERIA = {
    'start': '2026-11-20T01:00:00+00:00',
    'end': '2026-11-20T09:00:00+00:00',
    'setup_minutes': 0, 'turnaround_minutes': 0,
    'guest_count': 150, 'layout': 'Theatre',
    'facilities': ['Projector', 'Sound system'],
}


def _client(venues, bookings=None, blocks=None):
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id='coordinator-1'))
    tables = {name: MagicMock() for name in ['user_role', 'venue', 'venue_booking', 'venue_block']}
    client.table.side_effect = tables.__getitem__
    tables['user_role'].select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{'role': 'event_coordinator'}]
    tables['venue'].select.return_value.eq.return_value.execute.return_value.data = venues
    for name, rows in [('venue_booking', bookings or []), ('venue_block', blocks or [])]:
        query = tables[name].select.return_value
        query.eq.return_value = query
        query.lt.return_value = query
        query.gt.return_value = query
        query.execute.return_value.data = rows
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
    assert results[0]['occupied_start'] == CRITERIA['start']
    assert results[0]['temporary_unavailability'] == []
    booking_query = tables['venue_booking'].select.return_value
    booking_query.eq.assert_called_once_with('status', 'confirmed')
    booking_query.lt.assert_called_once_with('requested_start', CRITERIA['end'])
    booking_query.gt.assert_called_once_with('requested_end', CRITERIA['start'])
    block_query = tables['venue_block'].select.return_value
    block_query.eq.assert_called_once_with('status', 'active')
    block_query.lt.assert_called_once_with('start_datetime', CRITERIA['end'])
    block_query.gt.assert_called_once_with('end_datetime', CRITERIA['start'])


@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_setup_and_turnaround_expand_the_conflict_window(create_client):
    venue = {'venue_id': 'alcove', 'name': 'The Alcove', 'capacity': 180,
             'facilities': ['Projector'], 'supported_layouts': ['Theatre']}
    client, tables = _client([venue])
    create_client.return_value = client
    criteria = {
        **CRITERIA, 'facilities': ['Projector'],
        'setup_minutes': 60, 'turnaround_minutes': 30,
    }

    result = search_venues('token', criteria)[0]

    assert result['occupied_start'] == '2026-11-20T00:00:00+00:00'
    assert result['occupied_end'] == '2026-11-20T09:30:00+00:00'
    assert result['event_start'] == CRITERIA['start']
    assert result['event_end'] == CRITERIA['end']
    assert result['setup_minutes'] == 60
    assert result['turnaround_minutes'] == 30
    booking_query = tables['venue_booking'].select.return_value
    booking_query.lt.assert_called_once_with('requested_start', result['occupied_end'])
    booking_query.gt.assert_called_once_with('requested_end', result['occupied_start'])
    block_query = tables['venue_block'].select.return_value
    block_query.lt.assert_called_once_with('start_datetime', result['occupied_end'])
    block_query.gt.assert_called_once_with('end_datetime', result['occupied_start'])


@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_multi_venue_search_returns_only_complete_distinct_combinations(create_client):
    venues = [
        {'venue_id': 'alcove', 'name': 'The Alcove', 'capacity': 180,
         'facilities': ['Projector', 'Sound system'], 'supported_layouts': ['Theatre']},
        {'venue_id': 'workshop-b', 'name': 'Workshop Room B', 'capacity': 60,
         'facilities': ['Whiteboard', 'Video conferencing'], 'supported_layouts': ['Classroom']},
        {'venue_id': 'workshop-c', 'name': 'Workshop Room C', 'capacity': 60,
         'facilities': ['Whiteboard'], 'supported_layouts': ['Classroom']},
    ]
    client, _ = _client(venues)
    create_client.return_value = client
    criteria = {
        'start': CRITERIA['start'], 'end': CRITERIA['end'],
        'setup_minutes': 60, 'turnaround_minutes': 30, 'venue_count': 2,
        'venue_requirements': [
            {'guest_count': 150, 'layout': 'Theatre',
             'facilities': ['Projector', 'Sound system']},
            {'guest_count': 50, 'layout': 'Classroom',
             'facilities': ['Whiteboard', 'Video conferencing']},
        ],
    }

    results = search_venues('token', criteria)

    assert len(results) == 1
    assert [venue['venue_id'] for venue in results[0]['venues']] == ['alcove', 'workshop-b']
    assert results[0]['occupied_start'] == '2026-11-20T00:00:00+00:00'
    assert results[0]['occupied_end'] == '2026-11-20T09:30:00+00:00'


@patch('app.services.venue_search_service.create_authenticated_supabase_client')
def test_multi_venue_search_returns_none_when_any_requirement_has_no_match(create_client):
    venues = [{'venue_id': 'alcove', 'name': 'The Alcove', 'capacity': 180,
               'facilities': ['Projector'], 'supported_layouts': ['Theatre']}]
    client, _ = _client(venues)
    create_client.return_value = client
    criteria = {
        'start': CRITERIA['start'], 'end': CRITERIA['end'], 'venue_count': 2,
        'venue_requirements': [
            {'guest_count': 100, 'layout': 'Theatre', 'facilities': ['Projector']},
            {'guest_count': 50, 'layout': 'Classroom', 'facilities': ['Whiteboard']},
        ],
    }

    assert search_venues('token', criteria) == []


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
    ({'setup_minutes': -1}, 'Setup time'),
    ({'turnaround_minutes': 1.5}, 'Turnaround time'),
])
def test_invalid_search_criteria_are_rejected_before_database_access(change, message):
    criteria = {**CRITERIA, **change}
    with patch('app.services.venue_search_service.create_authenticated_supabase_client') as create_client:
        with pytest.raises(VenueSearchError, match=message):
            search_venues('token', criteria)
        create_client.assert_not_called()


def test_multi_venue_search_requires_one_requirement_per_venue():
    criteria = {
        'start': CRITERIA['start'], 'end': CRITERIA['end'], 'venue_count': 2,
        'venue_requirements': [
            {'guest_count': 100, 'layout': 'Theatre', 'facilities': ['Projector']},
        ],
    }
    with patch('app.services.venue_search_service.create_authenticated_supabase_client') as create_client:
        with pytest.raises(VenueSearchError, match='every required venue'):
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
