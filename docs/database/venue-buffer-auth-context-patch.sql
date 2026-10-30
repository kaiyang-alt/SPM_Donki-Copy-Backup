-- B1 auth-context compatibility patch for hosted Supabase.
-- Run the COMPLETE transaction as postgres, before configuring venue buffers.
-- Requires existing permission to SET ROLE b1_venue_buffer_executor.
-- Preserves function ownership, execute ACLs, audit behavior and Venue Staff
-- checks. Reads the same request identity as auth.uid(), without auth schema
-- access. No role membership, managed-auth grants, or application data changes.
-- Coordinate with the B1 owner; this is the approved buffer compatibility work.
BEGIN;
SET LOCAL statement_timeout='60s';
SELECT pg_advisory_xact_lock(212,8401);
DO $patch$
DECLARE v_definition text; v_had_create boolean;
BEGIN
  IF current_user<>'postgres' THEN RAISE EXCEPTION 'Run the complete B1 patch as postgres'; END IF;
  SELECT pg_get_functiondef('public.b1_save_venue_buffers(uuid,integer,integer,bigint,uuid)'::regprocedure)
    INTO v_definition;
  IF md5(replace(v_definition,E'\r\n',E'\n')) NOT IN ('75e66e4a08895191bd9e1e27e8a71a20','a108765b0f0c14422199543a7478364e','c1d39d356b8e5c228877564115887904','9136f2a79d3ccce06487288d91e30de8') THEN
    RAISE EXCEPTION 'B1 save definition changed; inspect before patching';
  END IF;
  v_definition := replace(v_definition,'actor uuid := auth.uid();',
    $identity$actor uuid := coalesce(
        nullif(current_setting('request.jwt.claim.sub',true),''),
        (nullif(current_setting('request.jwt.claims',true),'')::jsonb ->> 'sub')
    )::uuid;$identity$);
  v_had_create := has_schema_privilege('b1_venue_buffer_executor','public','CREATE');
  IF NOT v_had_create THEN GRANT CREATE ON SCHEMA public TO b1_venue_buffer_executor; END IF;
  SET LOCAL ROLE b1_venue_buffer_executor;
  EXECUTE v_definition;
  SET LOCAL ROLE postgres;
  IF NOT v_had_create THEN REVOKE CREATE ON SCHEMA public FROM b1_venue_buffer_executor; END IF;
END;
$patch$;
COMMIT;
