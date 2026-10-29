-- Keep Event Coordinator Lead ownership changes and their notifications atomic.
-- No schema, role, status, or RLS policy changes are introduced here.

create or replace function public.assign_event_coordinator_by_lead(
    p_event_id uuid,
    p_coordinator_id uuid
)
returns setof public.event
language plpgsql
security invoker
set search_path = pg_catalog, public
as $$
declare
    changed_event public.event%rowtype;
    changed_at timestamptz := clock_timestamp();
begin
    update public.event
       set coordinator_id = p_coordinator_id,
           updated_at = changed_at
     where event_id = p_event_id
       and status = 'requested'
       and coordinator_id is null
    returning * into changed_event;

    if not found then
        return;
    end if;

    insert into public.notification (
        notification_id, event_id, recipient_id, type, message, created_at
    ) values
    (
        gen_random_uuid(), changed_event.event_id, p_coordinator_id,
        'coordinator_assigned',
        'You have been assigned to ' || coalesce(changed_event.name, 'Untitled event') || '.',
        changed_at
    ),
    (
        gen_random_uuid(), changed_event.event_id, changed_event.organiser_id,
        'coordinator_assigned',
        'An Event Coordinator has been assigned to ' || coalesce(changed_event.name, 'Untitled event') || '.',
        changed_at
    );

    return next changed_event;
end;
$$;

create or replace function public.reassign_event_coordinator_by_lead(
    p_event_id uuid,
    p_coordinator_id uuid
)
returns setof public.event
language plpgsql
security invoker
set search_path = pg_catalog, public
as $$
declare
    previous_coordinator_id uuid;
    changed_event public.event%rowtype;
    changed_at timestamptz := clock_timestamp();
begin
    select coordinator_id
      into previous_coordinator_id
      from public.event
     where event_id = p_event_id
       and coordinator_id is not null
       and coordinator_id <> p_coordinator_id
     for update;

    if not found then
        return;
    end if;

    update public.event
       set coordinator_id = p_coordinator_id,
           updated_at = changed_at
     where event_id = p_event_id
       and coordinator_id = previous_coordinator_id
    returning * into changed_event;

    if not found then
        return;
    end if;

    insert into public.notification (
        notification_id, event_id, recipient_id, type, message, created_at
    ) values
    (
        gen_random_uuid(), changed_event.event_id, previous_coordinator_id,
        'coordinator_reassigned',
        'You are no longer assigned to ' || coalesce(changed_event.name, 'Untitled event') || '.',
        changed_at
    ),
    (
        gen_random_uuid(), changed_event.event_id, p_coordinator_id,
        'coordinator_reassigned',
        'You have been assigned to ' || coalesce(changed_event.name, 'Untitled event') || '.',
        changed_at
    ),
    (
        gen_random_uuid(), changed_event.event_id, changed_event.organiser_id,
        'coordinator_reassigned',
        'The Event Coordinator for ' || coalesce(changed_event.name, 'Untitled event') || ' has changed.',
        changed_at
    );

    return next changed_event;
end;
$$;

revoke all on function public.assign_event_coordinator_by_lead(uuid, uuid) from public;
revoke all on function public.reassign_event_coordinator_by_lead(uuid, uuid) from public;
grant execute on function public.assign_event_coordinator_by_lead(uuid, uuid) to authenticated;
grant execute on function public.reassign_event_coordinator_by_lead(uuid, uuid) to authenticated;

notify pgrst, 'reload schema';
