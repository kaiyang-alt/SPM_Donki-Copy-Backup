from datetime import datetime, timezone

from app.supabase_client import create_authenticated_supabase_client


class ReviewError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


AMENDABLE_FIELDS = {
    'name', 'purpose', 'description', 'preferred_start_datetime',
    'preferred_end_datetime', 'expected_attendance', 'venue_requirements',
    'accessibility_needs', 'layout_requirements', 'technical_support_required',
    'technical_requirements',
}


def _session(token):
    client = create_authenticated_supabase_client(token)
    try:
        user = client.auth.get_user(token).user
        if not user:
            raise ValueError('No user')
    except Exception as exc:
        raise ReviewError('Authentication is required.', 401) from exc
    return client, user.id


def _role(client, user_id, role):
    rows = client.table('user_role').select('role').eq('user_id', user_id).eq('role', role).execute().data
    if not rows:
        raise ReviewError('You do not have access to this review action.', 403)


def _event(client, user_id, event_id, coordinator=False):
    rows = client.table('event').select('*').eq('event_id', event_id).limit(1).execute().data
    if not rows:
        raise ReviewError('Event not found.', 404)
    event = rows[0]
    if coordinator:
        _role(client, user_id, 'event_coordinator')
        allowed = event.get('coordinator_id') == user_id
    else:
        allowed = user_id in (event.get('coordinator_id'), event.get('organiser_id'))
    if not allowed:
        raise ReviewError('You do not have access to this event.', 403)
    return event


def list_review_events(token):
    client, user_id = _session(token)
    _role(client, user_id, 'event_coordinator')
    return client.table('event').select('*').eq('coordinator_id', user_id).execute().data or []


def get_review(token, event_id):
    client, user_id = _session(token)
    event = _event(client, user_id, event_id)
    coordinator_name = _coordinator_name(client, event.get('coordinator_id'))
    actions = client.table('event_action_log').select('*').eq('event_id', event_id).order('created_at').execute().data or []
    reservations = client.table('equipment_reservation').select('quantity_requested,status,technical_requirements,equipment(name)').eq('event_id', event_id).execute().data or []
    return {
        'event': event,
        'coordinator_name': coordinator_name,
        'actions': actions,
        'equipment': reservations,
    }


def _coordinator_name(client, coordinator_id):
    if not coordinator_id:
        return None
    rows = (client.table('profile').select('name').eq('user_id', coordinator_id)
            .limit(1).execute().data or [])
    return rows[0].get('name') if rows else None


def submit_review(token, event_id, payload):
    client, user_id = _session(token)
    target = payload.get('status')
    if target not in {'changes_requested', 'planning'}:
        raise ReviewError('Select Clarification Required or Planning.')
    message = str(payload.get('message') or '').strip()
    if target == 'changes_requested' and not message:
        raise ReviewError('A clarification message is required.')
    event = _event(client, user_id, event_id, coordinator=True)
    if event.get('status') not in {'requested', 'changes_requested'}:
        raise ReviewError('This event is no longer awaiting review.', 409)
    return _record(client, user_id, event, {'status': target},
                   'clarification_requested' if target == 'changes_requested' else 'review_completed',
                   message or 'Event request reviewed; moved to planning.',
                   event['organiser_id'] if target == 'changes_requested' else None)


def respond_to_review(token, event_id, payload):
    client, user_id = _session(token)
    event = _event(client, user_id, event_id)
    _role(client, user_id, 'event_organiser')
    if event.get('organiser_id') != user_id:
        raise ReviewError('Only the event organiser may respond.', 403)
    if event.get('status') != 'changes_requested':
        raise ReviewError('This event is not awaiting clarification.', 409)
    message = str(payload.get('message') or '').strip()
    amendments = payload.get('amendments', {})
    if not isinstance(amendments, dict) or set(amendments) - AMENDABLE_FIELDS:
        raise ReviewError('Unsupported event amendments.')
    for key, value in amendments.items():
        if key == 'expected_attendance':
            if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
                raise ReviewError('Expected attendance must be an integer.')
        elif key == 'technical_support_required':
            if value is not None and not isinstance(value, bool):
                raise ReviewError('Technical support must be a boolean.')
        elif value is not None and not isinstance(value, str):
            raise ReviewError('Event text and date fields must be strings.')
    if not message:
        raise ReviewError('A clarification response is required.')
    # A response does not approve the event: the coordinator reviews it first.
    return _record(client, user_id, event, amendments, 'clarification_provided', message, event.get('coordinator_id'))


def _record(client, user_id, event, updates, action_type, message, recipient):
    now = datetime.now(timezone.utc).isoformat()
    # Conditional update prevents overwriting an event that has left review.
    result = (client.table('event').update({**updates, 'updated_at': now})
              .eq('event_id', event['event_id']).eq('status', event['status'])
              .eq('coordinator_id', event['coordinator_id']))
    result = (result.eq('updated_at', event['updated_at']) if event.get('updated_at')
              else result.is_('updated_at', 'null'))
    rows = result.execute().data
    if not rows:
        raise ReviewError('The request changed or cannot be updated. Reload it before retrying.', 409)
    try:
        log = client.table('event_action_log').insert({
            'event_id': event['event_id'], 'actor_id': user_id,
            'action_type': action_type, 'details': message,
            'old_status': event['status'], 'new_status': updates.get('status', event['status']),
            'created_at': now,
        }).execute()
        if not log.data:
            raise ValueError('Action not recorded')
        if recipient:
            notification = client.table('notification').insert({
                'event_id': event['event_id'], 'recipient_id': recipient,
                'type': action_type, 'message': message, 'created_at': now,
            }).execute()
            if not notification.data:
                raise ValueError('Notification not recorded')
    except Exception as exc:
        raise ReviewError('Event updated, but the message or notification could not be recorded. Reload the request and contact your team before retrying.', 502) from exc
    return rows[0]
