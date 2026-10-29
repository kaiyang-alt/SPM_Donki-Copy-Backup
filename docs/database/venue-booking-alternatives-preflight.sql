-- Read-only deployment inspection for the approved venue-alternatives change.
-- Run this complete SELECT in the shared project's Supabase SQL Editor as the
-- database owner. Return the single venue_booking_preflight result to the
-- developer preparing the migration. This is NOT the migration.
-- Returns schema/function definitions and aggregate counts only: no event names,
-- user records, booking details, passwords, keys or JWTs are requested.
-- No application table, policy, function or row is changed.

SELECT jsonb_pretty(jsonb_build_object(
  'tables', (
    SELECT coalesce(jsonb_agg(jsonb_build_object(
      'table', c.relname,
      'owner', pg_get_userbyid(c.relowner),
      'rls_enabled', c.relrowsecurity,
      'rls_forced', c.relforcerowsecurity
    ) ORDER BY c.relname), '[]'::jsonb)
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relkind IN ('r','p')
      AND c.relname IN ('event','venue','venue_booking','venue_block',
        'equipment','equipment_reservation','equipment_unavailability',
        'user_role','notification')
  ),
  'columns', (
    SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.table_name,x.ordinal_position), '[]'::jsonb)
    FROM (
      SELECT table_name,column_name,data_type,udt_name,is_nullable,
        column_default,ordinal_position
      FROM information_schema.columns
      WHERE table_schema='public' AND table_name IN (
        'event','venue','venue_booking','venue_block','equipment_reservation','notification')
    ) x
  ),
  'constraints', (
    SELECT coalesce(jsonb_agg(jsonb_build_object(
      'table', c.relname,'name', con.conname,
      'definition', pg_get_constraintdef(con.oid,true)
    ) ORDER BY c.relname,con.conname), '[]'::jsonb)
    FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relname IN (
      'event','venue','venue_booking','venue_block','equipment_reservation')
  ),
  'indexes', (
    SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.tablename,x.indexname), '[]'::jsonb)
    FROM (
      SELECT tablename,indexname,indexdef FROM pg_indexes
      WHERE schemaname='public' AND tablename IN (
        'venue_booking','venue_block','equipment_reservation')
    ) x
  ),
  'triggers', (
    SELECT coalesce(jsonb_agg(jsonb_build_object(
      'table', c.relname,'name', t.tgname,'enabled', t.tgenabled,
      'definition', pg_get_triggerdef(t.oid,true)
    ) ORDER BY c.relname,t.tgname), '[]'::jsonb)
    FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND NOT t.tgisinternal AND c.relname IN (
      'event','venue','venue_booking','venue_block','equipment',
      'equipment_reservation','equipment_unavailability')
  ),
  'functions', (
    SELECT coalesce(jsonb_agg(jsonb_build_object(
      'signature', p.oid::regprocedure::text,
      'owner', pg_get_userbyid(p.proowner),
      'security_definer', p.prosecdef,'settings', p.proconfig,
      'acl', p.proacl::text,'definition', pg_get_functiondef(p.oid)
    ) ORDER BY p.oid::regprocedure::text), '[]'::jsonb)
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
    WHERE n.nspname='public' AND p.prokind='f' AND (
      p.proname LIKE 'cs_equipment_%'
      OR p.proname IN ('accept_equipment_request','propose_equipment_quantity',
        'agree_equipment_proposal','confirm_venue_booking',
        'cs_technical_support_can_view_event','is_event_coordinator_lead')
      OR p.proname LIKE '%venue%'
      OR p.proname LIKE 'b1_%'
      OR p.oid IN (
        SELECT t.tgfoid FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid
        JOIN pg_namespace ns ON ns.oid=c.relnamespace
        WHERE ns.nspname='public' AND NOT t.tgisinternal AND c.relname IN (
          'event','venue','venue_booking','venue_block','equipment',
          'equipment_reservation','equipment_unavailability')
      )
    )
  ),
  'policies', (
    SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.tablename,x.policyname), '[]'::jsonb)
    FROM (
      SELECT tablename,policyname,permissive,roles,cmd,qual,with_check
      FROM pg_policies WHERE schemaname='public' AND tablename IN (
        'event','venue','venue_booking','venue_block','equipment',
        'equipment_reservation','equipment_unavailability','user_role','notification')
    ) x
  ),
  'table_grants', (
    SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.table_name,x.grantee,x.privilege_type), '[]'::jsonb)
    FROM (
      SELECT table_name,grantee,privilege_type FROM information_schema.table_privileges
      WHERE table_schema='public' AND grantee IN ('authenticated','anon','PUBLIC')
        AND table_name IN ('event','venue','venue_booking','venue_block',
          'equipment_reservation','notification')
    ) x
  ),
  'data_checks', jsonb_build_object(
    'events_with_multiple_confirmed_bookings', (
      SELECT count(*) FROM (
        SELECT event_id FROM public.venue_booking WHERE status='confirmed'
        GROUP BY event_id HAVING count(*)>1
      ) duplicates
    ),
    'overlapping_confirmed_booking_pairs', (
      SELECT count(*) FROM public.venue_booking a JOIN public.venue_booking b
        ON a.booking_id<b.booking_id AND a.venue_id=b.venue_id
        AND a.requested_start<b.requested_end AND a.requested_end>b.requested_start
      WHERE a.status='confirmed' AND b.status='confirmed'
    ),
    'confirmed_bookings_overlapping_active_blocks', (
      SELECT count(*) FROM public.venue_booking b
      WHERE b.status='confirmed' AND EXISTS (
        SELECT 1 FROM public.venue_block v WHERE v.venue_id=b.venue_id
          AND v.status='active' AND v.start_datetime<b.requested_end
          AND v.end_datetime>b.requested_start
      )
    ),
    'confirmed_bookings_with_missing_or_invalid_period_or_links', (
      SELECT count(*) FROM public.venue_booking
      WHERE status='confirmed' AND (event_id IS NULL OR venue_id IS NULL
        OR requested_start IS NULL OR requested_end IS NULL
        OR requested_start>=requested_end)
    ),
    'pending_bookings_on_events_with_confirmed_selection', (
      SELECT count(*) FROM public.venue_booking p
      WHERE p.status IN ('requested','tentative') AND EXISTS (
        SELECT 1 FROM public.venue_booking c
        WHERE c.event_id=p.event_id AND c.status='confirmed'
      )
    )
  )
)) AS venue_booking_preflight;

-- Supplement for the 27 October inspection: the live database contains B1
-- setup/turnaround-buffer logic absent from the repository baseline. Run ONLY
-- this SELECT if the original preflight result has already been supplied.
-- The four previously supplied B1 functions are deliberately excluded.
SELECT jsonb_pretty(jsonb_build_object(
  'remaining_buffer_functions', (
    SELECT coalesce(jsonb_agg(jsonb_build_object(
      'signature', p.oid::regprocedure::text,
      'owner', pg_get_userbyid(p.proowner),
      'security_definer', p.prosecdef,'settings', p.proconfig,
      'acl', p.proacl::text,'definition', pg_get_functiondef(p.oid)
    ) ORDER BY p.oid::regprocedure::text), '[]'::jsonb)
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
    WHERE n.nspname='public' AND p.prokind='f' AND p.proname LIKE 'b1_%'
      AND p.proname NOT IN ('b1_get_venue_buffer_operation',
        'b1_guard_venue_buffers','b1_list_venue_buffer_routing_exceptions',
        'b1_save_venue_buffers')
  ),
  'buffer_columns', (
    SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.table_name,x.ordinal_position), '[]'::jsonb)
    FROM (
      SELECT table_name,column_name,data_type,is_nullable,column_default,ordinal_position
      FROM information_schema.columns WHERE table_schema='public'
        AND (table_name LIKE '%buffer%' OR table_name LIKE 'b1_%')
    ) x
  ),
  'buffer_and_venue_constraints', (
    SELECT coalesce(jsonb_agg(jsonb_build_object(
      'table', c.relname,'name', con.conname,
      'definition', pg_get_constraintdef(con.oid,true)
    ) ORDER BY c.relname,con.conname), '[]'::jsonb)
    FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND (c.relname='venue'
      OR c.relname LIKE '%buffer%' OR c.relname LIKE 'b1_%')
  )
)) AS venue_buffer_supplement;
