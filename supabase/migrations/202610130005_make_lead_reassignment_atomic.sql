-- Replace an event's current Coordinator and create every required
-- notification in one transaction controlled by an Event Coordinator Lead.
create or replace function public.reassign_event_coordinator(
    p_event_id uuid,
    p_previous_coordinator_id uuid,
    p_replacement_coordinator_id uuid
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
    reassigned_event public.event%rowtype;
    replacement_name text;
    reassigned_at timestamptz := now();
begin
    if not public.is_event_coordinator_lead() then
        raise exception 'Event Coordinator Lead access is required.'
            using errcode = '42501';
    end if;

    if p_previous_coordinator_id = p_replacement_coordinator_id then
        raise exception 'Select a different Event Coordinator for reassignment.'
            using errcode = '22023';
    end if;

    select profile.name
      into replacement_name
      from public.profile
      join public.user_role
        on user_role.user_id = profile.user_id
       and user_role.role = 'event_coordinator'
     where profile.user_id = p_replacement_coordinator_id
       and profile.active is true;

    if not found then
        raise exception 'The selected user is not an active Event Coordinator.'
            using errcode = '22023';
    end if;

    update public.event
       set coordinator_id = p_replacement_coordinator_id,
           updated_at = reassigned_at
     where event_id = p_event_id
       and coordinator_id = p_previous_coordinator_id
    returning * into reassigned_event;

    if not found then
        raise exception 'The current assignment changed before reassignment completed.'
            using errcode = '40001';
    end if;

    insert into public.notification (
        event_id,
        recipient_id,
        type,
        message,
        created_at
    )
    values
        (
            reassigned_event.event_id,
            p_previous_coordinator_id,
            'coordinator_reassigned',
            'You are no longer assigned to '
                || coalesce(reassigned_event.name, 'Untitled event') || '.',
            reassigned_at
        ),
        (
            reassigned_event.event_id,
            p_replacement_coordinator_id,
            'coordinator_reassigned',
            'You have been assigned to '
                || coalesce(reassigned_event.name, 'Untitled event') || '.',
            reassigned_at
        ),
        (
            reassigned_event.event_id,
            reassigned_event.organiser_id,
            'coordinator_reassigned',
            'The Event Coordinator for '
                || coalesce(reassigned_event.name, 'Untitled event')
                || ' has changed.',
            reassigned_at
        );

    return jsonb_build_object(
        'event_id', reassigned_event.event_id,
        'name', reassigned_event.name,
        'status', reassigned_event.status,
        'organiser_id', reassigned_event.organiser_id,
        'coordinator_id', reassigned_event.coordinator_id,
        'coordinator_name', replacement_name,
        'previous_coordinator_id', p_previous_coordinator_id,
        'assigned_by', auth.uid(),
        'updated_at', reassigned_event.updated_at
    );
end;
$$;

revoke all on function public.reassign_event_coordinator(uuid, uuid, uuid)
from public;
grant execute on function public.reassign_event_coordinator(uuid, uuid, uuid)
to authenticated;
