-- Allow authenticated users to read only notifications addressed to them.
-- This does not grant access to another user's notifications.

drop policy if exists "Recipients can view their notifications"
on public.notification;

create policy "Recipients can view their notifications"
on public.notification
for select
to authenticated
using (recipient_id = auth.uid());

notify pgrst, 'reload schema';
