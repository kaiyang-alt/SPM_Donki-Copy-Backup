-- Permit Event Coordinator Leads to replace an existing event assignment.
drop policy if exists "Coordinator leads can view assigned events" on public.event;
create policy "Coordinator leads can view assigned events"
on public.event
for select
to authenticated
using (
    coordinator_id is not null
    and public.is_event_coordinator_lead()
);

drop policy if exists "Coordinator leads can reassign events" on public.event;
create policy "Coordinator leads can reassign events"
on public.event
for update
to authenticated
using (
    coordinator_id is not null
    and public.is_event_coordinator_lead()
)
with check (
    coordinator_id is not null
    and public.is_event_coordinator_lead()
    and exists (
        select 1
        from public.user_role coordinator_role
        where coordinator_role.user_id = coordinator_id
          and coordinator_role.role = 'event_coordinator'
    )
);

drop policy if exists "Coordinator leads can create reassignment notifications"
on public.notification;
create policy "Coordinator leads can create reassignment notifications"
on public.notification
for insert
to authenticated
with check (
    type = 'coordinator_reassigned'
    and public.is_event_coordinator_lead()
    and exists (
        select 1
        from public.event reassigned_event
        where reassigned_event.event_id = notification.event_id
          and (
              notification.recipient_id = reassigned_event.organiser_id
              or exists (
                  select 1
                  from public.user_role coordinator_role
                  where coordinator_role.user_id = notification.recipient_id
                    and coordinator_role.role = 'event_coordinator'
              )
          )
    )
);
