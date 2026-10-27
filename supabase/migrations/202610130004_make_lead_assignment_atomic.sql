-- Keep Event Coordinator assignment Lead-controlled even when another
-- permissive event UPDATE policy also applies to the authenticated user.
create or replace function public.enforce_coordinator_assignment_actor()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if old.coordinator_id is distinct from new.coordinator_id
       and not public.is_event_coordinator_lead() then
        raise exception 'Only an Event Coordinator Lead may change the Event Coordinator.'
            using errcode = '42501';
    end if;
    return new;
end;
$$;

revoke all on function public.enforce_coordinator_assignment_actor() from public;

drop trigger if exists trg_enforce_coordinator_assignment_actor on public.event;
create trigger trg_enforce_coordinator_assignment_actor
before update of coordinator_id on public.event
for each row
execute function public.enforce_coordinator_assignment_actor();

-- Assign the event and create both required notifications in one transaction.
-- Any validation or insert failure rolls the complete operation back.
create or replace function public.assign_unassigned_event(
    p_event_id uuid,
    p_coordinator_id uuid
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
    assigned_event public.event%rowtype;
    coordinator_name text;
    assigned_at timestamptz := now();
begin
    if not public.is_event_coordinator_lead() then
        raise exception 'Event Coordinator Lead access is required.'
            using errcode = '42501';
    end if;

    select profile.name
      into coordinator_name
      from public.profile
      join public.user_role
        on user_role.user_id = profile.user_id
       and user_role.role = 'event_coordinator'
     where profile.user_id = p_coordinator_id
       and profile.active is true;

    if not found then
        raise exception 'The selected user is not an active Event Coordinator.'
            using errcode = '22023';
    end if;

    update public.event
       set coordinator_id = p_coordinator_id,
           updated_at = assigned_at
     where event_id = p_event_id
       and status = 'requested'
       and coordinator_id is null
    returning * into assigned_event;

    if not found then
        raise exception 'The event request is no longer available for assignment.'
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
            assigned_event.event_id,
            p_coordinator_id,
            'coordinator_assigned',
            'You have been assigned to '
                || coalesce(assigned_event.name, 'Untitled event') || '.',
            assigned_at
        ),
        (
            assigned_event.event_id,
            assigned_event.organiser_id,
            'coordinator_assigned',
            'An Event Coordinator has been assigned to '
                || coalesce(assigned_event.name, 'Untitled event') || '.',
            assigned_at
        );

    return jsonb_build_object(
        'event_id', assigned_event.event_id,
        'name', assigned_event.name,
        'status', assigned_event.status,
        'organiser_id', assigned_event.organiser_id,
        'coordinator_id', assigned_event.coordinator_id,
        'coordinator_name', coordinator_name,
        'assigned_by', auth.uid(),
        'updated_at', assigned_event.updated_at
    );
end;
$$;

revoke all on function public.assign_unassigned_event(uuid, uuid) from public;
grant execute on function public.assign_unassigned_event(uuid, uuid) to authenticated;
