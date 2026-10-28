-- Read-only verification AFTER the complete alternatives migration commits.
-- Run as the database owner; return the single result to the implementation owner.
-- No test accounts, application records or secrets are returned or changed.
SELECT jsonb_pretty(jsonb_build_object(
  'booking_layout_column', EXISTS(SELECT 1 FROM information_schema.columns
    WHERE table_schema='public' AND table_name='venue_booking' AND column_name='setup_layout' AND data_type='text'),
  'one_confirmed_index', (SELECT indexdef FROM pg_indexes
    WHERE schemaname='public' AND tablename='venue_booking' AND indexname='cs_venue_one_confirmed_per_event'),
  'confirmation_rpc', to_regprocedure('public.confirm_venue_booking(uuid)')::text,
  'confirmation_authenticated_execute', has_function_privilege('authenticated','public.confirm_venue_booking(uuid)','EXECUTE'),
  'confirmation_anonymous_execute', has_function_privilege('anon','public.confirm_venue_booking(uuid)','EXECUTE'),
  'buffer_save_uses_shared_lock', position('pg_advisory_xact_lock(212,8401)' IN
    pg_get_functiondef('public.b1_save_venue_buffers(uuid,integer,integer,bigint,uuid)'::regprocedure))>0,
  'equipment_uses_venue_decision', position('cs_venue_period_available' IN
    pg_get_functiondef('public.cs_equipment_schedule_fits(uuid,jsonb)'::regprocedure))>0,
  'buffer_save_owner', (SELECT pg_get_userbyid(proowner) FROM pg_proc
    WHERE oid='public.b1_save_venue_buffers(uuid,integer,integer,bigint,uuid)'::regprocedure),
  'buffer_save_reads_request_identity', position('actor uuid := coalesce(' IN
    pg_get_functiondef('public.b1_save_venue_buffers(uuid,integer,integer,bigint,uuid)'::regprocedure))>0,
  'checker_owner_can_execute_buffer_calculator', has_function_privilege('postgres',
    'public.b1_occupied_period(timestamptz,timestamptz,integer,integer)','EXECUTE'),
  'enabled_validation_triggers', (SELECT jsonb_agg(t.tgname ORDER BY t.tgname)
    FROM pg_trigger t WHERE t.tgrelid IN ('public.venue_booking'::regclass,'public.venue_block'::regclass)
      AND t.tgname IN ('cs_venue_booking_validate','cs_venue_booking_cancel','cs_venue_block_validate',
        'cs_equipment_booking_lock','cs_equipment_venue_block_lock') AND t.tgenabled='O'),
  'duplicate_confirmed_events', (SELECT count(*) FROM (
    SELECT event_id FROM public.venue_booking WHERE status='confirmed' GROUP BY event_id HAVING count(*)>1
  ) duplicates),
  'confirmed_occupied_periods_valid', (SELECT coalesce(bool_and(public.cs_venue_period_available(
    venue_id,requested_start,requested_end,booking_id)),true) FROM public.venue_booking WHERE status='confirmed')
)) AS venue_booking_alternatives_verification;
