-- Replace automatic assignment with Event Coordinator Lead-controlled assignment.
drop trigger if exists trg_event_auto_assign_coordinator on public.event;

-- This narrowly scoped helper avoids recursive user_role RLS evaluation while
-- still requiring the caller's authenticated user id and exact Lead role.
create or replace function public.is_event_coordinator_lead()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.user_role
        where user_id = auth.uid()
          and role = 'event_coordinator_lead'
    );
$$;

revoke all on function public.is_event_coordinator_lead() from public;
grant execute on function public.is_event_coordinator_lead() to authenticated;

drop policy if exists "Coordinator leads can view requested events" on public.event;
create policy "Coordinator leads can view requested events"
on public.event
for select
to authenticated
using (
    status = 'requested'
    and public.is_event_coordinator_lead()
);

drop policy if exists "Coordinator leads can assign requested events" on public.event;
create policy "Coordinator leads can assign requested events"
on public.event
for update
to authenticated
using (
    status = 'requested'
    and coordinator_id is null
    and public.is_event_coordinator_lead()
)
with check (
    status = 'requested'
    and coordinator_id is not null
    and public.is_event_coordinator_lead()
    and exists (
        select 1
        from public.user_role coordinator_role
        where coordinator_role.user_id = coordinator_id
          and coordinator_role.role = 'event_coordinator'
    )
);

drop policy if exists "Coordinator leads can view coordinator roles" on public.user_role;
create policy "Coordinator leads can view coordinator roles"
on public.user_role
for select
to authenticated
using (
    role = 'event_coordinator'
    and public.is_event_coordinator_lead()
);

drop policy if exists "Coordinator leads can view coordinator profiles" on public.profile;
create policy "Coordinator leads can view coordinator profiles"
on public.profile
for select
to authenticated
using (
    public.is_event_coordinator_lead()
    and exists (
        select 1
        from public.user_role coordinator_role
        where coordinator_role.user_id = profile.user_id
          and coordinator_role.role = 'event_coordinator'
    )
);

drop policy if exists "Coordinator leads can create assignment notifications"
on public.notification;
create policy "Coordinator leads can create assignment notifications"
on public.notification
for insert
to authenticated
with check (
    type = 'coordinator_assigned'
    and public.is_event_coordinator_lead()
    and exists (
        select 1
        from public.event assigned_event
        where assigned_event.event_id = notification.event_id
          and assigned_event.status = 'requested'
          and notification.recipient_id in (
              assigned_event.organiser_id,
              assigned_event.coordinator_id
          )
    )
);
