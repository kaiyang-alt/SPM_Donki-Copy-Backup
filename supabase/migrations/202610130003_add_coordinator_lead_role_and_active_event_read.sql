-- Add the approved Event Coordinator Lead role to the existing role constraint.
alter table public.user_role
drop constraint if exists user_role_role_check;

alter table public.user_role
drop constraint if exists user_roles_role_check;

alter table public.user_role
add constraint user_role_role_check
check (
    role in (
        'event_organiser',
        'event_coordinator',
        'event_coordinator_lead',
        'venue_staff',
        'technical_support',
        'attendee'
    )
);

-- Event Coordinator Leads oversee every active event in the current model.
drop policy if exists "Coordinator leads can view active events" on public.event;
create policy "Coordinator leads can view active events"
on public.event
for select
to authenticated
using (
    status in ('requested', 'changes_requested', 'planning', 'confirmed')
    and public.is_event_coordinator_lead()
);
