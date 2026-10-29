-- Shared workflow compatibility for auto-assigned events already in planning.
-- Initial review records approved/rejected/changes_requested; resource work
-- requires approved and final event confirmation requires approved -> confirmed.
-- Run as the existing table owner. No event rows or status values are changed.
-- Apply alongside equipment-pending-venue-priority-patch.sql, not the full
-- historical equipment migration. Existing equipment SQL already uses approved.
BEGIN;
SET LOCAL statement_timeout = '60s';
SELECT pg_advisory_xact_lock(212,8401);

DO $patch$
DECLARE
  expression text;
  old_states constant text := 'ARRAY[''requested''::text, ''changes_requested''::text]';
  new_states constant text := 'ARRAY[''requested''::text, ''changes_requested''::text, ''planning''::text]';
BEGIN
  SELECT pg_get_expr(polwithcheck,polrelid) INTO expression
  FROM pg_policy WHERE polrelid='public.event_action_log'::regclass
    AND polname='Assigned coordinators can create review action logs'
    AND polcmd='a' AND polpermissive;
  IF expression IS NULL THEN
    RAISE EXCEPTION 'Expected Coordinator audit INSERT policy is missing; inspect before deployment';
  END IF;
  -- Accept only the supplied 29 October definition or the exact patched version.
  IF md5(regexp_replace(btrim(replace(expression,new_states,old_states)), '\s+', ' ', 'g'))
      <> '4d1748f67de83649c9646eb64d477fba' THEN
    RAISE EXCEPTION 'Coordinator audit policy changed since inspection; export it before deployment';
  END IF;
  EXECUTE format('ALTER POLICY %I ON public.event_action_log WITH CHECK (%s)',
    'Assigned coordinators can create review action logs',
    replace(expression,old_states,new_states));
END;
$patch$;

COMMIT;

-- Expect true. Actor role, assignment, target state and event checks are retained.
SELECT position('''planning''::text' IN pg_get_expr(polwithcheck,polrelid))>0
  AS planning_review_audit_enabled
FROM pg_policy WHERE polrelid='public.event_action_log'::regclass
  AND polname='Assigned coordinators can create review action logs';
