-- Local-only regression for the supplied Supabase membership failure.
-- Load venue_booking_alternatives_fixture.sql in a fresh PostgreSQL 17 cluster
-- bootstrapped as migration_permissions_admin with database postgres. Run this
-- file as that administrator; it creates a non-superuser postgres deployment
-- role matching the supplied non-inheriting B1 membership.
-- NEVER run this fixture/role simulation against Supabase.
CREATE ROLE postgres LOGIN BYPASSRLS NOINHERIT;
ALTER DATABASE postgres OWNER TO postgres;
DO $$ DECLARE r record; BEGIN
 FOR r IN SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relkind='r' LOOP
  EXECUTE format('ALTER TABLE public.%I OWNER TO postgres',r.relname);
 END LOOP;
 FOR r IN SELECT p.oid::regprocedure::text signature FROM pg_proc p
  JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prokind='f'
   AND p.proowner=(SELECT oid FROM pg_roles WHERE rolname='migration_permissions_admin') LOOP
  EXECUTE 'ALTER FUNCTION '||r.signature||' OWNER TO postgres';
 END LOOP;
END; $$;
GRANT USAGE ON SCHEMA auth TO postgres;
GRANT EXECUTE ON FUNCTION auth.uid() TO postgres;
GRANT b1_venue_buffer_executor TO postgres WITH INHERIT FALSE;
GRANT b1_venue_buffer_executor TO postgres WITH SET TRUE;
-- This membership is only for the authenticated smoke test, not migration DDL.
GRANT authenticated TO postgres WITH INHERIT FALSE;
GRANT authenticated TO postgres WITH SET TRUE;
-- Hosted Supabase custom roles cannot necessarily use the managed auth schema.
REVOKE USAGE ON SCHEMA auth FROM b1_venue_buffer_executor;
\connect postgres postgres
CREATE TEMP TABLE original_b1_permissions AS
 SELECT proowner,proacl FROM pg_proc
 WHERE oid='public.b1_save_venue_buffers(uuid,integer,integer,bigint,uuid)'::regprocedure;
DO $$ BEGIN
 IF (SELECT rolsuper FROM pg_roles WHERE rolname=current_user)
 OR pg_has_role(current_user,'b1_venue_buffer_executor','USAGE')
 OR NOT pg_has_role(current_user,'b1_venue_buffer_executor','MEMBER')
 OR has_schema_privilege('b1_venue_buffer_executor','public','CREATE') THEN
  RAISE EXCEPTION 'Fixture must match non-superuser, non-inheriting postgres with no executor schema CREATE';
 END IF;
END; $$;
\ir ../docs/database/venue-buffer-auth-context-patch.sql
\ir ../docs/database/venue-buffer-auth-context-patch.sql
-- The standalone patch must work before the main migration/configuration step.
BEGIN;
SET LOCAL ROLE b1_venue_buffer_executor;
SET LOCAL request.jwt.claim.sub='';
DO $$ BEGIN
 BEGIN
  PERFORM public.b1_save_venue_buffers(NULL,15,15,0,gen_random_uuid());
  RAISE EXCEPTION 'Missing user identity was accepted';
 EXCEPTION WHEN insufficient_privilege THEN
  IF SQLERRM<>'B1_VENUE_STAFF_REQUIRED' THEN RAISE; END IF;
 END;
END; $$;
SET LOCAL request.jwt.claim.sub='00000000-0000-0000-0000-000000000004';
DO $$ BEGIN
 BEGIN
  PERFORM public.b1_save_venue_buffers(NULL,15,15,0,gen_random_uuid());
  RAISE EXCEPTION 'Input validation was bypassed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'B1_REQUIRED_INPUT_MISSING_OR_INVALID' THEN RAISE; END IF;
 END;
END; $$;
ROLLBACK;
\ir ../docs/database/venue-booking-alternatives-migration.sql
\ir ../docs/database/venue-booking-alternatives-migration.sql
DO $$ BEGIN
 IF current_user<>'postgres' OR (SELECT rolsuper FROM pg_roles WHERE rolname=current_user)
 OR pg_has_role(current_user,'b1_venue_buffer_executor','USAGE')
 OR has_schema_privilege('b1_venue_buffer_executor','public','CREATE') THEN
  RAISE EXCEPTION 'Migration changed deployment-role or executor privileges';
 END IF;
 IF has_schema_privilege('b1_venue_buffer_executor','auth','USAGE') THEN
  RAISE EXCEPTION 'B1 auth-context patch must not grant managed auth schema access';
 END IF;
 IF EXISTS(SELECT 1 FROM pg_proc p CROSS JOIN original_b1_permissions old
  WHERE p.oid='public.b1_save_venue_buffers(uuid,integer,integer,bigint,uuid)'::regprocedure
   AND (p.proowner<>old.proowner OR p.proacl IS DISTINCT FROM old.proacl)) THEN
  RAISE EXCEPTION 'Migration changed B1 save ownership or execute grants';
 END IF;
 IF NOT has_function_privilege('postgres','public.b1_occupied_period(timestamptz,timestamptz,integer,integer)','EXECUTE')
 OR has_function_privilege('authenticated','public.b1_occupied_period(timestamptz,timestamptz,integer,integer)','EXECUTE')
 OR has_function_privilege('anon','public.b1_occupied_period(timestamptz,timestamptz,integer,integer)','EXECUTE') THEN
  RAISE EXCEPTION 'Buffer-calculator execute must be scoped to the trusted checker owner';
 END IF;
END; $$;
BEGIN;
INSERT INTO venue(venue_id,name) VALUES('70000000-0000-0000-0000-000000000001','Permission test venue');
SET LOCAL request.jwt.claim.sub='00000000-0000-0000-0000-000000000004';
SET LOCAL ROLE b1_venue_buffer_executor;
SELECT b1_save_venue_buffers('70000000-0000-0000-0000-000000000001',15,15,0,gen_random_uuid());
SET LOCAL ROLE postgres;
SET LOCAL request.jwt.claim.sub='';
INSERT INTO event(event_id,organiser_id,name,status)
VALUES('70000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','Permission test','planning');
INSERT INTO venue_booking(booking_id,event_id,venue_id,requested_start,requested_end,status,setup_layout)
VALUES('70000000-0000-0000-0000-000000000003','70000000-0000-0000-0000-000000000002',
 '70000000-0000-0000-0000-000000000001','2026-11-20 09:00+08','2026-11-20 12:00+08','requested','Theatre');
SET LOCAL ROLE authenticated;
SET LOCAL request.jwt.claim.sub='00000000-0000-0000-0000-000000000004';
SELECT confirm_venue_booking('70000000-0000-0000-0000-000000000003');
ROLLBACK;
\connect postgres migration_permissions_admin
-- Restore this isolated fixture's postgres role for subsequent synthetic tests.
ALTER ROLE postgres SUPERUSER INHERIT;
\connect postgres postgres
