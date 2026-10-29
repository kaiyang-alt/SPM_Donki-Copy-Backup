from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.app import app
from app.services.event_review_service import (
    APPROVAL_DEFAULT_MESSAGE, ReviewError, get_review, list_review_events,
    respond_to_review, submit_review,
)


@pytest.fixture
def database():
    client = MagicMock()
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id='coord'))
    event = {'event_id': 'evt', 'organiser_id': 'org', 'coordinator_id': 'coord',
             'status': 'requested', 'updated_at': '2026-09-18T00:00:00+00:00'}
    tables = {name: MagicMock() for name in ['event', 'user_role', 'event_action_log', 'notification', 'equipment_reservation']}
    client.table.side_effect = tables.__getitem__
    tables['event'].select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [event]
    tables['user_role'].select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{'role': 'event_coordinator'}]
    update = tables['event'].update.return_value
    update.eq.return_value = update
    update.is_.return_value = update
    update.execute.return_value.data = [{**event, 'status': 'changes_requested'}]
    for name in ['event_action_log', 'notification']:
        tables[name].insert.return_value.execute.return_value.data = [{'id': 'saved'}]
    with patch('app.services.event_review_service.create_authenticated_supabase_client', return_value=client):
        yield client, tables, event


def test_clarification_records_message_status_actor_and_recipient(database):
    _, tables, _ = database
    submit_review('token', 'evt', {'status': 'changes_requested', 'message': 'How many microphones?'})
    assert tables['event'].update.call_args.args[0]['status'] == 'changes_requested'
    log = tables['event_action_log'].insert.call_args.args[0]
    assert (log['actor_id'], log['details'], log['old_status'], log['new_status']) == (
        'coord', 'How many microphones?', 'requested', 'changes_requested')
    assert tables['notification'].insert.call_args.args[0]['recipient_id'] == 'org'


def test_listing_only_selects_assigned_events(database):
    _, tables, _ = database
    tables['event'].select.return_value.eq.return_value.execute.return_value.data = [{'event_id': 'evt'}]
    assert list_review_events('token') == [{'event_id': 'evt'}]
    tables['event'].select.return_value.eq.assert_called_once_with('coordinator_id', 'coord')


def test_organiser_can_read_message_history_and_equipment(database):
    client, tables, event = database
    client.auth.get_user.return_value.user.id = 'org'
    history = [{'action_type': 'clarification_requested', 'details': 'How many microphones?'}]
    equipment = [{'equipment': {'name': 'Microphone'}, 'quantity_requested': 3}]
    tables['event_action_log'].select.return_value.eq.return_value.order.return_value.execute.return_value.data = history
    tables['equipment_reservation'].select.return_value.eq.return_value.execute.return_value.data = equipment
    assert get_review('token', 'evt') == {'event': event, 'actions': history, 'equipment': equipment}


def test_unrelated_user_cannot_read_clarification_history(database):
    client, tables, _ = database
    client.auth.get_user.return_value.user.id = 'unrelated'
    with pytest.raises(ReviewError) as error:
        get_review('token', 'evt')
    assert error.value.status == 403
    tables['event_action_log'].select.assert_not_called()


@pytest.mark.parametrize('status', ['requested', 'planning', 'changes_requested'])
def test_coordinator_can_approve_eligible_request(database, status):
    _, tables, event = database
    event['status'] = status
    submit_review('token', 'evt', {'status': 'approved', 'message': 'Ready to proceed.'})
    assert tables['event'].update.call_args.args[0]['status'] == 'approved'
    log = tables['event_action_log'].insert.call_args.args[0]
    assert (log['action_type'], log['actor_id'], log['old_status'], log['new_status']) == (
        'event_approved', 'coord', status, 'approved')
    assert log['created_at']
    notification = tables['notification'].insert.call_args.args[0]
    assert (notification['recipient_id'], notification['type'], notification['message']) == (
        'org', 'event_approved', 'Ready to proceed.')
    assert notification['created_at'] == log['created_at']


def test_approval_without_feedback_uses_default_notification(database):
    _, tables, _ = database
    submit_review('token', 'evt', {'status': 'approved', 'message': '  '})
    notification = tables['notification'].insert.call_args.args[0]
    assert notification['message'] == APPROVAL_DEFAULT_MESSAGE
    assert tables['event_action_log'].insert.call_args.args[0]['details'] == APPROVAL_DEFAULT_MESSAGE


@pytest.mark.parametrize('status', ['requested', 'planning', 'changes_requested'])
def test_rejection_records_required_feedback_and_notifies_organiser(database, status):
    _, tables, event = database
    event['status'] = status
    submit_review('token', 'evt', {'status': 'rejected', 'message': 'Safety details are incomplete.'})
    assert tables['event'].update.call_args.args[0]['status'] == 'rejected'
    log = tables['event_action_log'].insert.call_args.args[0]
    assert (log['action_type'], log['old_status'], log['new_status'], log['details']) == (
        'event_rejected', status, 'rejected', 'Safety details are incomplete.')
    notification = tables['notification'].insert.call_args.args[0]
    assert (notification['recipient_id'], notification['type']) == ('org', 'event_rejected')


def test_rejection_without_feedback_has_no_side_effects(database):
    _, tables, _ = database
    with pytest.raises(ReviewError, match='rejection feedback'):
        submit_review('token', 'evt', {'status': 'rejected', 'message': ' '})
    tables['event'].update.assert_not_called()
    tables['event_action_log'].insert.assert_not_called()
    tables['notification'].insert.assert_not_called()


def test_review_interface_has_distinct_approve_and_reject_controls():
    source = Path('app/static/js/event-review.js').read_text(encoding='utf-8')
    assert 'data-review-decision="approved">Approve</button>' in source
    assert 'data-review-decision="rejected">Reject</button>' in source


@pytest.mark.parametrize('failure', ['assignment', 'role', 'state', 'message', 'status'])
def test_prohibited_review_never_writes(database, failure):
    _, tables, event = database
    payload = {'status': 'changes_requested', 'message': 'Please clarify.'}
    if failure == 'assignment': event['coordinator_id'] = 'other'
    if failure == 'role':
        tables['user_role'].select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    if failure == 'state': event['status'] = 'confirmed'
    if failure == 'message': payload['message'] = ' '
    if failure == 'status': payload['status'] = 'pending'
    with pytest.raises(ReviewError): submit_review('token', 'evt', payload)
    tables['event'].update.assert_not_called()
    tables['event_action_log'].insert.assert_not_called()


def test_organiser_response_amends_documented_fields_without_approval(database):
    client, tables, event = database
    client.auth.get_user.return_value.user.id = 'org'
    event['status'] = 'changes_requested'
    respond_to_review('token', 'evt', {'message': 'Three microphones.', 'amendments': {'technical_requirements': '3 microphones'}})
    updates = tables['event'].update.call_args.args[0]
    assert updates['technical_requirements'] == '3 microphones'
    assert 'status' not in updates
    assert tables['event_action_log'].insert.call_args.args[0]['new_status'] == 'changes_requested'
    assert tables['notification'].insert.call_args.args[0]['recipient_id'] == 'coord'


def test_organiser_cannot_amend_assignment_or_status(database):
    client, tables, event = database
    client.auth.get_user.return_value.user.id = 'org'
    event['status'] = 'changes_requested'
    with pytest.raises(ReviewError):
        respond_to_review('token', 'evt', {'message': 'Approve me', 'amendments': {'status': 'planning'}})
    tables['event'].update.assert_not_called()


def test_coordinator_cannot_respond_on_behalf_of_organiser(database):
    _, tables, event = database
    event['status'] = 'changes_requested'
    with pytest.raises(ReviewError) as error:
        respond_to_review('token', 'evt', {'message': 'Organiser response'})
    assert error.value.status == 403
    tables['event'].update.assert_not_called()


def test_concurrent_update_does_not_send_message(database):
    _, tables, _ = database
    tables['event'].update.return_value.execute.return_value.data = []
    with pytest.raises(ReviewError) as error:
        submit_review('token', 'evt', {'status': 'approved'})
    assert error.value.status == 409
    tables['event_action_log'].insert.assert_not_called()


def test_partial_write_failure_is_reported(database):
    _, tables, _ = database
    tables['notification'].insert.return_value.execute.side_effect = RuntimeError('RLS denied')
    with pytest.raises(ReviewError, match='Event updated') as error:
        submit_review('token', 'evt', {'status': 'changes_requested', 'message': 'Clarify please'})
    assert error.value.status == 502


def test_review_routes_require_authentication_and_object_payload():
    client = app.test_client()
    assert client.get('/api/event-reviews').status_code == 401
    assert client.post('/api/event-reviews/evt/decision', json=['approved']).status_code == 400


@patch('app.routes.event_reviews.submit_review')
def test_decision_route_passes_authenticated_input(operation):
    operation.return_value = {'event_id': 'evt', 'status': 'approved'}
    response = app.test_client().post('/api/event-reviews/evt/decision',
        headers={'Authorization': 'Bearer token'}, json={'status': 'approved'})
    assert response.status_code == 200
    operation.assert_called_once_with('token', 'evt', {'status': 'approved'})


@patch("app.routes.auth.login_user")
def test_coordinator_credentials_use_existing_login_endpoint(login):
    login.return_value = {
        "access_token": "token",
        "roles": ["event_coordinator"],
    }

    response = app.test_client().post(
        "/auth/application-login",
        json={
            "email": "coordinator@example.test",
            "password": "password",
        },
    )

    assert response.status_code == 200
    assert response.get_json()["roles"] == ["event_coordinator"]
    login.assert_called_once_with("coordinator@example.test", "password")
