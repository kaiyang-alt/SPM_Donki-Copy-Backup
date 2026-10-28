-- Approved venue-alternatives deployment, 27 October 2026.
-- Run the WHOLE transaction as postgres during a coordinated deployment pause.
-- Requires the equipment proposal migration and the inspected B1 buffer helpers.
-- Does not delete/backfill bookings, invent legacy layouts, change event status,
-- implement notifications, or change the 30-minute equipment transfer gap.
-- Deploy the matching application after this database checkpoint. Do not rerun
-- the old equipment proposal migration afterwards: it restores old venue rules.
BEGIN;
SET LOCAL statement_timeout = '60s';
SELECT pg_advisory_xact_lock(212,8401);

-- Live-definition drift checks are inserted below before any schema change.
DO $definitions$
BEGIN
  IF current_user<>'postgres' OR current_setting('transaction_isolation')<>'read committed' THEN
    RAISE EXCEPTION 'Run the complete migration as postgres at READ COMMITTED';
  END IF;
  IF coalesce(md5(replace(pg_get_functiondef(to_regprocedure('cs_equipment_schedule_fits(uuid,jsonb)')), E'\r\n', E'\n')),'missing') NOT IN ('fe020fc3cdee97e17f463547e20d52c1','9fd4795e999d6c0ccb591350d8fa3d21') THEN
    RAISE EXCEPTION 'Inspected definition changed: cs_equipment_schedule_fits; rerun preflight before deployment';
  END IF;
  IF coalesce(md5(replace(pg_get_functiondef(to_regprocedure('b1_save_venue_buffers(uuid,integer,integer,bigint,uuid)')), E'\r\n', E'\n')),'missing') NOT IN ('75e66e4a08895191bd9e1e27e8a71a20','a108765b0f0c14422199543a7478364e','c1d39d356b8e5c228877564115887904','9136f2a79d3ccce06487288d91e30de8') THEN
    RAISE EXCEPTION 'Inspected definition changed: b1_save_venue_buffers; rerun preflight before deployment';
  END IF;
  IF coalesce(md5(replace(pg_get_functiondef(to_regprocedure('b1_occupied_period(timestamp with time zone,timestamp with time zone,integer,integer)')), E'\r\n', E'\n')),'missing') <> 'd2c1aeb1053201c19062cf3f96bb69c2' THEN
    RAISE EXCEPTION 'Inspected dependency changed: b1_occupied_period';
  END IF;
  IF coalesce(md5(replace(pg_get_functiondef(to_regprocedure('cs_equipment_write_lock()')), E'\r\n', E'\n')),'missing') <> 'f41d15869d7edffe9714a0d02bef1af6' THEN
    RAISE EXCEPTION 'Inspected dependency changed: cs_equipment_write_lock';
  END IF;
  IF coalesce(md5(replace(pg_get_functiondef(to_regprocedure('cs_equipment_fit_tasks(jsonb,integer,jsonb,integer)')), E'\r\n', E'\n')),'missing') <> 'a90657edc0200f3eef34dfffd2a24b11' THEN
    RAISE EXCEPTION 'Inspected dependency changed: cs_equipment_fit_tasks';
  END IF;
  IF (SELECT count(*) FROM pg_trigger WHERE tgrelid IN ('public.venue_booking'::regclass,'public.venue_block'::regclass) AND tgname IN ('cs_equipment_booking_lock','cs_equipment_venue_block_lock') AND tgenabled='O')<>2 THEN
    RAISE EXCEPTION 'Expected booking/block statement locks are not enabled';
  END IF;
END;
$definitions$;

-- Membership without inheritance requires an explicit owner-role switch.
-- Check SET permission before changing schema; PostgreSQL checks session_user.
SET LOCAL ROLE b1_venue_buffer_executor;
SET LOCAL ROLE postgres;

ALTER TABLE public.venue_booking ADD COLUMN IF NOT EXISTS setup_layout text;

-- A trusted, read-only decision protects callers from RLS-hidden commitments.
-- Existing table RLS still authorises the originating booking/block writes.
CREATE OR REPLACE FUNCTION public.cs_venue_period_available(
  p_venue_id uuid,p_start timestamptz,p_end timestamptz,
  p_exclude_booking_id uuid DEFAULT NULL
) RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER
SET search_path=pg_catalog,public AS $$
DECLARE v_venue public.venue; v_period tstzrange;
BEGIN
  IF auth.uid() IS NULL THEN
    IF session_user <> 'postgres' THEN RAISE EXCEPTION 'Venue authentication is required' USING ERRCODE='42501'; END IF;
  ELSIF NOT EXISTS(SELECT 1 FROM public.user_role WHERE user_id=auth.uid()
      AND role IN ('event_coordinator','venue_staff','technical_support')) THEN
    RAISE EXCEPTION 'Venue access is not permitted' USING ERRCODE='42501';
  END IF;
  SELECT * INTO v_venue FROM public.venue WHERE venue_id=p_venue_id;
  IF NOT FOUND OR v_venue.active IS NOT TRUE THEN RETURN false; END IF;
  v_period := public.b1_occupied_period(p_start,p_end,v_venue.setup_minutes,v_venue.turnaround_minutes);
  IF EXISTS(SELECT 1 FROM public.venue_booking b WHERE b.venue_id=p_venue_id
      AND (b.status IS NULL OR b.status NOT IN ('requested','tentative','confirmed','rejected','cancelled')
        OR (b.status='confirmed' AND (b.requested_start IS NULL OR b.requested_end IS NULL
          OR NOT isfinite(b.requested_start) OR NOT isfinite(b.requested_end)
          OR b.requested_start>=b.requested_end))))
    OR EXISTS(SELECT 1 FROM public.venue_block b WHERE b.venue_id=p_venue_id
      AND (b.status IS NULL OR b.status NOT IN ('active','cancelled')
        OR (b.status='active' AND (b.start_datetime IS NULL OR b.end_datetime IS NULL
          OR NOT isfinite(b.start_datetime) OR NOT isfinite(b.end_datetime)
          OR b.start_datetime>=b.end_datetime)))) THEN
    RAISE EXCEPTION 'Venue commitments contain invalid or ambiguous data';
  END IF;
  RETURN NOT EXISTS(SELECT 1 FROM public.venue_booking b
    WHERE b.venue_id=p_venue_id AND b.status='confirmed'
      AND (p_exclude_booking_id IS NULL OR b.booking_id<>p_exclude_booking_id)
      AND public.b1_occupied_period(b.requested_start,b.requested_end,
        v_venue.setup_minutes,v_venue.turnaround_minutes) && v_period)
    AND NOT EXISTS(SELECT 1 FROM public.venue_block b
      WHERE b.venue_id=p_venue_id AND b.status='active'
        AND tstzrange(b.start_datetime,b.end_datetime,'[)') && v_period);
END;
$$;
REVOKE ALL ON FUNCTION public.cs_venue_period_available(uuid,timestamptz,timestamptz,uuid) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.cs_venue_period_available(uuid,timestamptz,timestamptz,uuid) TO authenticated;

-- Preserve inspected signatures, ownership, ACLs and all unrelated logic.
CREATE OR REPLACE FUNCTION public.cs_equipment_schedule_fits(p_equipment_id uuid, p_extra jsonb DEFAULT '[]'::jsonb)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
  v_total integer; v_tasks jsonb := '[]'; v_states jsonb := '[]'; v_row record;
  v_booking public.venue_booking; v_count integer; v_i integer; v_result jsonb;
BEGIN
  IF auth.uid() IS NULL THEN
    IF session_user <> 'postgres' THEN RAISE EXCEPTION 'Equipment access is not permitted' USING ERRCODE='42501'; END IF;
  ELSIF NOT EXISTS(SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role IN ('technical_support','event_coordinator','venue_staff')) THEN
    RAISE EXCEPTION 'Equipment access is not permitted' USING ERRCODE='42501';
  END IF;
  SELECT total_quantity INTO v_total FROM public.equipment WHERE equipment_id=p_equipment_id;
  IF NOT FOUND OR v_total IS NULL OR v_total < 0 THEN RAISE EXCEPTION 'Equipment stock is missing, inaccessible, or invalid'; END IF;
  FOR v_row IN
    SELECT r.event_id,r.start_datetime s,r.end_datetime e,coalesce(r.quantity_suggested,r.quantity_requested) q
    FROM public.equipment_reservation r WHERE r.equipment_id=p_equipment_id AND r.status='reserved'
    UNION ALL
    SELECT x.event_id,x.start_datetime,x.end_datetime,x.quantity_suggested
    FROM jsonb_to_recordset(p_extra) x(event_id uuid,start_datetime timestamptz,end_datetime timestamptz,quantity_suggested integer)
  LOOP
    IF v_row.s IS NULL OR v_row.e IS NULL OR v_row.s>=v_row.e OR v_row.q IS NULL OR v_row.q<=0 THEN
      RAISE EXCEPTION 'Equipment commitments contain invalid or ambiguous data';
    END IF;
    SELECT count(*) INTO v_count FROM public.venue_booking WHERE event_id=v_row.event_id AND status='confirmed';
    SELECT * INTO v_booking FROM public.venue_booking WHERE event_id=v_row.event_id AND status='confirmed';
    IF v_count<>1 OR NOT FOUND OR v_booking.venue_id IS NULL THEN
      RAISE EXCEPTION 'Exactly one confirmed venue booking is required';
    END IF;
    IF v_booking.requested_start IS DISTINCT FROM v_row.s OR v_booking.requested_end IS DISTINCT FROM v_row.e THEN
      RAISE EXCEPTION 'Equipment proposal period must match the confirmed venue booking';
    END IF;
    IF NOT public.cs_venue_period_available(v_booking.venue_id,v_row.s,v_row.e,v_booking.booking_id) THEN
      RAISE EXCEPTION 'Confirmed venue is unavailable for the proposed period';
    END IF;
    IF v_row.q>v_total THEN RETURN false; END IF;
    FOR v_i IN 1..v_row.q LOOP
      v_tasks := v_tasks || jsonb_build_array(jsonb_build_object('kind','event','s',extract(epoch FROM v_row.s),
        'e',extract(epoch FROM v_row.e),'venue',v_booking.venue_id));
    END LOOP;
  END LOOP;
  FOR v_row IN SELECT * FROM public.equipment_unavailability WHERE equipment_id=p_equipment_id LOOP
    IF v_row.status IS NULL OR v_row.status NOT IN ('active','cancelled') THEN RAISE EXCEPTION 'Equipment commitments contain invalid or ambiguous data'; END IF;
    IF v_row.status='cancelled' THEN CONTINUE; END IF;
    IF v_row.start_datetime IS NULL OR v_row.end_datetime IS NULL OR v_row.start_datetime>=v_row.end_datetime
       OR v_row.quantity_unavailable IS NULL OR v_row.quantity_unavailable<=0 THEN RAISE EXCEPTION 'Equipment commitments contain invalid or ambiguous data'; END IF;
    IF v_row.quantity_unavailable>v_total THEN RETURN false; END IF;
    FOR v_i IN 1..v_row.quantity_unavailable LOOP
      v_tasks := v_tasks || jsonb_build_array(jsonb_build_object('kind','maintenance','s',extract(epoch FROM v_row.start_datetime),
        'e',extract(epoch FROM v_row.end_datetime),'venue',NULL));
    END LOOP;
  END LOOP;
  SELECT coalesce(jsonb_agg(value ORDER BY (value->>'s')::numeric,(value->>'e')::numeric,value->>'kind'),'[]') INTO v_tasks FROM jsonb_array_elements(v_tasks);
  IF v_total>0 THEN
    FOR v_i IN 1..least(v_total,jsonb_array_length(v_tasks)) LOOP
      v_states := v_states || jsonb_build_array(jsonb_build_object('last_end',NULL,'venue',NULL,'gaps','[]'::jsonb));
    END LOOP;
  END IF;
  v_result := public.cs_equipment_fit_tasks(v_tasks,0,v_states,100000);
  RETURN (v_result->>'fits')::boolean;
END;
$function$;

-- Replace as the existing owner, not as a superuser. CREATE OR REPLACE also
-- needs schema CREATE. If absent, expose that privilege only inside this
-- transaction and revoke it before commit; other sessions never see the grant.
-- Save-function ownership/ACLs and role-membership options remain unchanged.
-- The new postgres-owned checker needs EXECUTE on the pure buffer calculator;
-- grant only that function, without inheriting the whole executor role.
DO $replace_b1$
DECLARE v_had_schema_create boolean;
BEGIN
  v_had_schema_create := has_schema_privilege('b1_venue_buffer_executor','public','CREATE');
  IF NOT v_had_schema_create THEN
    GRANT CREATE ON SCHEMA public TO b1_venue_buffer_executor;
  END IF;
  SET LOCAL ROLE b1_venue_buffer_executor;
  GRANT EXECUTE ON FUNCTION public.b1_occupied_period(timestamptz,timestamptz,integer,integer) TO postgres;
  EXECUTE $definition$CREATE OR REPLACE FUNCTION public.b1_save_venue_buffers(p_venue_id uuid, p_setup_minutes integer, p_turnaround_minutes integer, p_expected_revision bigint, p_operation_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
 SET "TimeZone" TO 'UTC'
AS $function$
DECLARE
    actor uuid := coalesce(
        nullif(current_setting('request.jwt.claim.sub',true),''),
        (nullif(current_setting('request.jwt.claims',true),'')::jsonb ->> 'sub')
    )::uuid;
    prior public.venue_buffer_operation%ROWTYPE;
    old_setup integer;
    old_turnaround integer;
    current_revision bigint;
    resulting_revision bigint;
    old_conflicts jsonb := '[]'::jsonb;
    new_conflicts jsonb;
    changed_conflicts jsonb := '[]'::jsonb;
    limitations jsonb;
    notices jsonb := '[]'::jsonb;
    exceptions jsonb := '[]'::jsonb;
    outcome jsonb;
    same_values boolean;
    target_event record;
    recipient uuid;
    event_found boolean;
    notice_id uuid;
    routing_reason text;
    stamp timestamptz := pg_catalog.transaction_timestamp();
BEGIN
    IF actor IS NULL OR NOT EXISTS (
        SELECT 1 FROM public.user_role ur
        WHERE ur.user_id = actor AND ur.role = 'venue_staff'
    ) THEN
        RAISE EXCEPTION 'B1_VENUE_STAFF_REQUIRED' USING ERRCODE = '42501';
    END IF;
    IF p_venue_id IS NULL OR p_operation_id IS NULL
       OR p_expected_revision IS NULL OR p_expected_revision < 0
       OR p_setup_minutes IS NULL OR p_turnaround_minutes IS NULL THEN
        RAISE EXCEPTION 'B1_REQUIRED_INPUT_MISSING_OR_INVALID';
    END IF;
    IF p_setup_minutes < 0 OR p_turnaround_minutes < 0 THEN
        RAISE EXCEPTION 'B1_NEGATIVE_DURATION';
    END IF;
    IF p_setup_minutes = 0 OR p_turnaround_minutes = 0 THEN
        RAISE EXCEPTION 'B1_ZERO_DECISION_REQUIRED';
    END IF;

    -- Unlocked read of an immutable committed receipt; historical, not a new save.
    SELECT op.* INTO prior FROM public.venue_buffer_operation op
    WHERE op.operation_id = p_operation_id;
    IF FOUND THEN
        IF prior.actor_id IS DISTINCT FROM actor
           OR prior.venue_id IS DISTINCT FROM p_venue_id
           OR prior.expected_revision IS DISTINCT FROM p_expected_revision
           OR prior.setup_minutes IS DISTINCT FROM p_setup_minutes
           OR prior.turnaround_minutes IS DISTINCT FROM p_turnaround_minutes
        THEN
            RAISE EXCEPTION 'B1_OPERATION_TOKEN_REUSED';
        END IF;
        RETURN prior.outcome;
    END IF;

    -- Venue alternatives share the equipment/booking lock before venue locks.
    IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'Venue buffer saves require READ COMMITTED isolation';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(212,8401);

    SELECT v.setup_minutes, v.turnaround_minutes, v.buffer_config_revision
    INTO old_setup, old_turnaround, current_revision
    FROM public.venue v WHERE v.venue_id = p_venue_id FOR UPDATE OF v;
    IF NOT FOUND THEN
        -- A concurrent committed save followed by deletion can become visible here.
    SELECT op.* INTO prior FROM public.venue_buffer_operation op
    WHERE op.operation_id = p_operation_id;
    IF FOUND THEN
        IF prior.actor_id IS DISTINCT FROM actor
           OR prior.venue_id IS DISTINCT FROM p_venue_id
           OR prior.expected_revision IS DISTINCT FROM p_expected_revision
           OR prior.setup_minutes IS DISTINCT FROM p_setup_minutes
           OR prior.turnaround_minutes IS DISTINCT FROM p_turnaround_minutes
        THEN
            RAISE EXCEPTION 'B1_OPERATION_TOKEN_REUSED';
        END IF;
        RETURN prior.outcome;
    END IF;

        RAISE EXCEPTION 'B1_VENUE_NOT_FOUND';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_operation_id::text, 14101::bigint)
    );
    SELECT op.* INTO prior FROM public.venue_buffer_operation op
    WHERE op.operation_id = p_operation_id;
    IF FOUND THEN
        IF prior.actor_id IS DISTINCT FROM actor
           OR prior.venue_id IS DISTINCT FROM p_venue_id
           OR prior.expected_revision IS DISTINCT FROM p_expected_revision
           OR prior.setup_minutes IS DISTINCT FROM p_setup_minutes
           OR prior.turnaround_minutes IS DISTINCT FROM p_turnaround_minutes
        THEN
            RAISE EXCEPTION 'B1_OPERATION_TOKEN_REUSED';
        END IF;
        RETURN prior.outcome;
    END IF;

    IF p_expected_revision <> current_revision THEN
        RAISE EXCEPTION 'B1_STALE_CONFIGURATION_REVISION';
    END IF;
    same_values := old_setup IS NOT DISTINCT FROM p_setup_minutes
                   AND old_turnaround IS NOT DISTINCT FROM p_turnaround_minutes;
    resulting_revision := current_revision;
    IF NOT same_values THEN
        IF current_revision = 9223372036854775807::bigint THEN
            RAISE EXCEPTION 'B1_REVISION_EXHAUSTED';
        END IF;
        resulting_revision := current_revision + 1;
    END IF;

    -- Common protocol: venue first, then event UUID order. Reassignment waits.
    PERFORM e.event_id FROM public.event e
    WHERE EXISTS (
        SELECT 1 FROM public.venue_booking b
        WHERE b.venue_id = p_venue_id AND b.event_id = e.event_id
          AND b.status IN ('confirmed','requested','tentative')
    )
    ORDER BY e.event_id FOR SHARE OF e;

    IF old_setup IS NOT NULL AND old_turnaround IS NOT NULL THEN
        old_conflicts := public.b1_buffer_conflicts(
            p_venue_id, old_setup, old_turnaround
        );
    END IF;
    new_conflicts := public.b1_buffer_conflicts(
        p_venue_id, p_setup_minutes, p_turnaround_minutes
    );

    -- Authoritative blockers have already raised in b1_buffer_conflicts.
    -- Only the approved B2 uncertainty may remain in a committed response.
    SELECT COALESCE(pg_catalog.jsonb_agg(q.item ORDER BY q.item::text), '[]'::jsonb)
    INTO limitations
    FROM (
        SELECT pg_catalog.jsonb_build_object(
            'booking_id', b.booking_id,
            'reason', CASE
                WHEN b.requested_start IS NULL OR b.requested_end IS NULL
                  OR NOT pg_catalog.isfinite(b.requested_start)
                  OR NOT pg_catalog.isfinite(b.requested_end)
                  OR b.requested_start >= b.requested_end
                THEN 'hold_schedule_unassessable_pending_owner'
                ELSE 'hold_validity_unavailable' END
        ) AS item
        FROM public.venue_booking b
        WHERE b.venue_id = p_venue_id
          AND b.status IN ('requested','tentative')
    ) q;
    IF old_setup IS NULL OR old_turnaround IS NULL THEN
        limitations := limitations || pg_catalog.jsonb_build_array(
            pg_catalog.jsonb_build_object('reason', 'old_configuration_unconfigured')
        );
    END IF;

    IF NOT same_values THEN
        SELECT COALESCE(pg_catalog.jsonb_agg(n.item ORDER BY n.item::text), '[]'::jsonb)
        INTO changed_conflicts
        FROM pg_catalog.jsonb_array_elements(new_conflicts) AS n(item)
        WHERE n.item->>'assessment' = 'identified'
          AND NOT EXISTS (
              SELECT 1
              FROM pg_catalog.jsonb_array_elements(old_conflicts) AS o(item)
              WHERE o.item = n.item
          );

        UPDATE public.venue
        SET setup_minutes = p_setup_minutes,
            turnaround_minutes = p_turnaround_minutes,
            buffer_config_revision = resulting_revision
        WHERE venue_id = p_venue_id;

        -- Derive both event sides; consolidate all booking IDs for each event.
        FOR target_event IN
            WITH affected AS (
                SELECT (x.item->>'event_id')::uuid AS event_id,
                       (x.item->>'booking_id')::uuid AS booking_id
                FROM pg_catalog.jsonb_array_elements(changed_conflicts) x(item)
                UNION
                SELECT (x.item->>'other_event_id')::uuid,
                       (x.item->>'other_booking_id')::uuid
                FROM pg_catalog.jsonb_array_elements(changed_conflicts) x(item)
                WHERE x.item->>'kind' = 'booking_booking'
            )
            SELECT a.event_id,
                   pg_catalog.jsonb_agg(a.booking_id ORDER BY a.booking_id) AS booking_ids
            FROM affected a GROUP BY a.event_id ORDER BY a.event_id NULLS FIRST
        LOOP
            recipient := NULL;
            routing_reason := NULL;
            SELECT e.coordinator_id INTO recipient
            FROM public.event e WHERE e.event_id = target_event.event_id;
            event_found := FOUND;
            IF NOT event_found THEN
                routing_reason := 'missing_event';
            ELSIF recipient IS NULL THEN
                routing_reason := 'missing_assigned_coordinator';
            ELSIF NOT EXISTS (
                SELECT 1 FROM public.user_role ur
                WHERE ur.user_id = recipient AND ur.role = 'event_coordinator'
            ) THEN
                routing_reason := 'assigned_coordinator_role_missing';
            END IF;

            IF routing_reason IS NOT NULL THEN
                exceptions := exceptions || pg_catalog.jsonb_build_array(
                    pg_catalog.jsonb_build_object(
                        'event_id', target_event.event_id,
                        'booking_ids', target_event.booking_ids,
                        'configuration_revision', resulting_revision,
                        'reason', routing_reason
                    )
                );
            ELSE
                notice_id := pg_catalog.gen_random_uuid();
                INSERT INTO public.notification (
                    notification_id, event_id, recipient_id, type,
                    message, created_at, read_at
                ) VALUES (
                    notice_id, target_event.event_id, recipient,
                    'venue_buffer_conflict',
                    'Venue operating durations changed; your retained booking arrangement at venue '
                    || p_venue_id::text
                    || ' requires review due to an occupied-period conflict. Configuration revision '
                    || resulting_revision::text || '.',
                    stamp, NULL
                );
                notices := notices || pg_catalog.jsonb_build_array(
                    pg_catalog.jsonb_build_object(
                        'notification_id', notice_id,
                        'event_id', target_event.event_id,
                        'recipient_id', recipient
                    )
                );
            END IF;
        END LOOP;
    END IF;

    outcome := pg_catalog.jsonb_build_object(
        'contract_version', 'B1-OCC-v1',
        'operation_id', p_operation_id,
        'venue_id', p_venue_id,
        'configuration_saved', true,
        'no_op', same_values,
        'setup_minutes', p_setup_minutes,
        'turnaround_minutes', p_turnaround_minutes,
        'configuration_revision', resulting_revision,
        'recorded_at', stamp,
        'conflicts', new_conflicts,
        'assessment_limitations', limitations,
        'authoritative_assessment_complete', true,
        'assessment_complete', NOT EXISTS (
            SELECT 1 FROM pg_catalog.jsonb_array_elements(limitations) l(item)
            WHERE l.item->>'reason' <> 'old_configuration_unconfigured'
        ),
        'notification_scope', 'identified_conflict_delta_only',
        'notification_status', CASE
            WHEN pg_catalog.jsonb_array_length(exceptions) > 0 THEN 'incomplete_routing'
            WHEN pg_catalog.jsonb_array_length(notices) > 0 THEN 'persisted'
            ELSE 'not_required' END,
        'persisted_notices', notices,
        'routing_exceptions', exceptions
    );
    INSERT INTO public.venue_buffer_operation (
        operation_id, actor_id, venue_id, expected_revision,
        setup_minutes, turnaround_minutes, result_revision, recorded_at, outcome
    ) VALUES (
        p_operation_id, actor, p_venue_id, p_expected_revision,
        p_setup_minutes, p_turnaround_minutes, resulting_revision, stamp, outcome
    );
    RETURN outcome;
END
$function$;$definition$;
  SET LOCAL ROLE postgres;
  IF NOT v_had_schema_create THEN
    REVOKE CREATE ON SCHEMA public FROM b1_venue_buffer_executor;
  END IF;
END;
$replace_b1$;


-- New submissions require their own layout. Null historical layout is retained
-- and must be reviewed before a pending legacy booking can be confirmed.
CREATE OR REPLACE FUNCTION public.cs_venue_booking_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
BEGIN
  IF NEW.status IS NULL THEN RAISE EXCEPTION 'Venue booking status is required'; END IF;
  IF TG_OP='UPDATE' AND OLD.status='confirmed' AND
    ROW(NEW.event_id,NEW.venue_id,NEW.requested_start,NEW.requested_end,NEW.setup_layout)
      IS DISTINCT FROM ROW(OLD.event_id,OLD.venue_id,OLD.requested_start,OLD.requested_end,OLD.setup_layout) THEN
    RAISE EXCEPTION 'Release the confirmed venue before changing its arrangement';
  END IF;
  IF NEW.status IN ('cancelled','rejected') THEN RETURN NEW; END IF;
  IF TG_OP='UPDATE' AND OLD.status='confirmed' AND NEW.status='confirmed' THEN RETURN NEW; END IF;
  IF nullif(btrim(NEW.setup_layout),'') IS NULL THEN RAISE EXCEPTION 'A booking setup layout is required'; END IF;
  IF NEW.status='confirmed' THEN
    IF auth.uid() IS NOT NULL AND NOT EXISTS(SELECT 1 FROM public.user_role
      WHERE user_id=auth.uid() AND role='venue_staff') THEN
      RAISE EXCEPTION 'Venue Staff access is required' USING ERRCODE='42501';
    END IF;
    IF auth.uid() IS NULL AND session_user<>'postgres' THEN
      RAISE EXCEPTION 'Venue Staff access is required' USING ERRCODE='42501';
    END IF;
    IF TG_OP='UPDATE' AND OLD.status NOT IN ('requested','tentative') THEN
      RAISE EXCEPTION 'Only pending venue requests can be confirmed';
    END IF;
    NEW.decided_by := auth.uid(); NEW.decided_at := clock_timestamp(); NEW.decision_reason := NULL;
  ELSIF TG_OP='INSERT' AND NEW.status<>'requested' THEN
    RAISE EXCEPTION 'New venue alternatives must use requested status';
  END IF;
  IF NOT public.cs_venue_period_available(NEW.venue_id,NEW.requested_start,NEW.requested_end,NEW.booking_id) THEN
    RAISE EXCEPTION 'Venue is unavailable for the occupied period';
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.cs_venue_booking_guard() FROM PUBLIC,anon;

CREATE OR REPLACE FUNCTION public.cs_venue_cancel_alternatives()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
BEGIN
  IF NEW.status='confirmed' THEN
    UPDATE public.venue_booking SET status='cancelled',decided_by=NEW.decided_by,
      decided_at=NEW.decided_at,
      decision_reason=concat_ws(E'\n',nullif(decision_reason,''),
        'Automatically cancelled: venue alternative '||NEW.booking_id::text||' confirmed.')
      WHERE event_id=NEW.event_id AND booking_id<>NEW.booking_id
        AND status IN ('requested','tentative');
  END IF;
  RETURN NULL;
END;
$$;
REVOKE ALL ON FUNCTION public.cs_venue_cancel_alternatives() FROM PUBLIC,anon;

CREATE OR REPLACE FUNCTION public.cs_venue_block_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE v_venue public.venue;
BEGIN
  IF NEW.status='cancelled' THEN RETURN NEW; END IF;
  IF NEW.status IS DISTINCT FROM 'active' OR NEW.start_datetime IS NULL OR NEW.end_datetime IS NULL
    OR NOT isfinite(NEW.start_datetime) OR NOT isfinite(NEW.end_datetime)
    OR NEW.start_datetime>=NEW.end_datetime THEN
    RAISE EXCEPTION 'An active venue block requires a valid bounded period';
  END IF;
  SELECT * INTO v_venue FROM public.venue WHERE venue_id=NEW.venue_id;
  IF EXISTS(SELECT 1 FROM public.venue_booking b WHERE b.venue_id=NEW.venue_id AND b.status='confirmed'
    AND public.b1_occupied_period(b.requested_start,b.requested_end,
      v_venue.setup_minutes,v_venue.turnaround_minutes)
      && tstzrange(NEW.start_datetime,NEW.end_datetime,'[)')) THEN
    RAISE EXCEPTION 'Venue block overlaps a confirmed occupied period';
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.cs_venue_block_guard() FROM PUBLIC,anon;

-- Reuse inspected statement locks; replacing their definitions is unnecessary.
CREATE OR REPLACE TRIGGER cs_venue_booking_validate BEFORE INSERT OR UPDATE ON public.venue_booking
FOR EACH ROW EXECUTE FUNCTION public.cs_venue_booking_guard();
CREATE OR REPLACE TRIGGER cs_venue_booking_cancel AFTER INSERT OR UPDATE OF status ON public.venue_booking
FOR EACH ROW EXECUTE FUNCTION public.cs_venue_cancel_alternatives();
CREATE OR REPLACE TRIGGER cs_venue_block_validate BEFORE INSERT OR UPDATE ON public.venue_block
FOR EACH ROW EXECUTE FUNCTION public.cs_venue_block_guard();

CREATE UNIQUE INDEX IF NOT EXISTS cs_venue_one_confirmed_per_event
ON public.venue_booking(event_id) WHERE status='confirmed';

CREATE OR REPLACE FUNCTION public.confirm_venue_booking(p_booking_id uuid)
RETURNS public.venue_booking LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE v_booking public.venue_booking;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS(SELECT 1 FROM public.user_role
    WHERE user_id=auth.uid() AND role='venue_staff') THEN
    RAISE EXCEPTION 'Venue Staff access is required' USING ERRCODE='42501';
  END IF;
  IF current_setting('transaction_isolation')<>'read committed' THEN
    RAISE EXCEPTION 'Venue confirmation requires READ COMMITTED isolation';
  END IF;
  PERFORM pg_advisory_xact_lock(212,8401);
  SELECT * INTO v_booking FROM public.venue_booking WHERE booking_id=p_booking_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Venue booking not found or inaccessible'; END IF;
  IF v_booking.status='confirmed' THEN RETURN v_booking; END IF;
  IF v_booking.status IS NULL OR v_booking.status NOT IN ('requested','tentative') THEN
    RAISE EXCEPTION 'Only pending venue requests can be confirmed';
  END IF;
  IF EXISTS(SELECT 1 FROM public.venue_booking WHERE event_id=v_booking.event_id AND status='confirmed') THEN
    RAISE EXCEPTION 'This event already has a confirmed venue';
  END IF;
  UPDATE public.venue_booking SET status='confirmed' WHERE booking_id=p_booking_id
    AND status IN ('requested','tentative') RETURNING * INTO v_booking;
  IF NOT FOUND THEN RAISE EXCEPTION 'Venue booking changed or cannot be updated' USING ERRCODE='42501'; END IF;
  RETURN v_booking;
END;
$$;
REVOKE ALL ON FUNCTION public.confirm_venue_booking(uuid) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.confirm_venue_booking(uuid) TO authenticated;

-- Existing records are inspected, never silently cancelled or relabelled.
-- Buffer changes intentionally retain arrangements under the B1 contract, so
-- resolve pre-existing occupied conflicts before applying this migration.
DO $validate$
DECLARE v_booking record; v_equipment uuid;
BEGIN
  IF EXISTS(SELECT 1 FROM public.venue_booking p WHERE p.status IN ('requested','tentative')
    AND EXISTS(SELECT 1 FROM public.venue_booking c WHERE c.event_id=p.event_id AND c.status='confirmed')) THEN
    RAISE EXCEPTION 'Review existing pending alternatives alongside confirmed selections before migration';
  END IF;
  FOR v_booking IN SELECT * FROM public.venue_booking WHERE status='confirmed' LOOP
    IF NOT public.cs_venue_period_available(v_booking.venue_id,v_booking.requested_start,
      v_booking.requested_end,v_booking.booking_id) THEN
      RAISE EXCEPTION 'Review existing occupied venue conflicts before migration';
    END IF;
  END LOOP;
  FOR v_equipment IN SELECT DISTINCT equipment_id FROM public.equipment_reservation WHERE status='reserved' LOOP
    IF NOT public.cs_equipment_schedule_fits(v_equipment) THEN
      RAISE EXCEPTION 'Review existing equipment commitments before migration';
    END IF;
  END LOOP;
END;
$validate$;

NOTIFY pgrst,'reload schema';
COMMIT;
