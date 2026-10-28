-- Synthetic local-only fixture. NEVER run against Supabase.
-- Run using psql -v ON_ERROR_STOP=1 -f tests/venue_booking_alternatives_fixture.sql
\ir equipment_proposals_fixture.sql
\ir ../docs/database/equipment-acceptance-draft.sql
\ir ../docs/database/equipment-proposals-migration.sql
ALTER TABLE venue ADD COLUMN setup_minutes integer, ADD COLUMN turnaround_minutes integer,
 ADD COLUMN buffer_config_revision bigint NOT NULL DEFAULT 0;
ALTER TABLE venue_booking ADD COLUMN requested_by uuid REFERENCES profile,
 ADD COLUMN requested_at timestamptz, ADD COLUMN decided_by uuid REFERENCES profile,
 ADD COLUMN decided_at timestamptz, ADD COLUMN decision_reason text;
CREATE ROLE b1_venue_buffer_executor NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public,auth TO b1_venue_buffer_executor;
GRANT EXECUTE ON FUNCTION auth.uid() TO b1_venue_buffer_executor;
CREATE TABLE venue_buffer_operation(operation_id uuid PRIMARY KEY,actor_id uuid,venue_id uuid,
 expected_revision bigint,setup_minutes integer,turnaround_minutes integer,
 result_revision bigint,recorded_at timestamptz,outcome jsonb);
GRANT SELECT ON user_role,event,venue,venue_booking,venue_block TO b1_venue_buffer_executor;
GRANT UPDATE ON venue,event TO b1_venue_buffer_executor;
GRANT SELECT,INSERT ON venue_buffer_operation TO b1_venue_buffer_executor;
CREATE TABLE notification(notification_id uuid PRIMARY KEY,event_id uuid,recipient_id uuid,
 type text,message text,created_at timestamptz,read_at timestamptz);
GRANT INSERT ON notification TO b1_venue_buffer_executor;
CREATE POLICY b1_role_read ON user_role FOR SELECT TO b1_venue_buffer_executor USING(true);
CREATE POLICY b1_event_read ON event FOR SELECT TO b1_venue_buffer_executor USING(true);
CREATE POLICY b1_event_lock ON event FOR UPDATE TO b1_venue_buffer_executor USING(true) WITH CHECK(false);
CREATE POLICY b1_venue_read ON venue FOR SELECT TO b1_venue_buffer_executor USING(true);
CREATE POLICY b1_venue_write ON venue FOR UPDATE TO b1_venue_buffer_executor USING(true) WITH CHECK(true);
CREATE POLICY b1_booking_read ON venue_booking FOR SELECT TO b1_venue_buffer_executor USING(true);
CREATE POLICY b1_block_read ON venue_block FOR SELECT TO b1_venue_buffer_executor USING(true);

CREATE OR REPLACE FUNCTION public.b1_occupied_period(p_start timestamp with time zone, p_end timestamp with time zone, p_setup integer, p_turnaround integer)
 RETURNS tstzrange
 LANGUAGE plpgsql
 IMMUTABLE
 SET search_path TO 'pg_catalog', 'pg_temp'
 SET "TimeZone" TO 'UTC'
AS $function$
DECLARE
    occupied_start timestamptz;
    occupied_end timestamptz;
    lower_bound CONSTANT timestamptz := '0001-01-01 00:00:00+00';
    upper_bound CONSTANT timestamptz := '9999-12-31 23:59:59.999999+00';
BEGIN
    IF p_setup IS NULL OR p_turnaround IS NULL THEN
        RAISE EXCEPTION 'B1_CONFIGURATION_REQUIRED';
    END IF;
    IF p_setup < 0 OR p_turnaround < 0 THEN
        RAISE EXCEPTION 'B1_NEGATIVE_DURATION';
    END IF;
    IF p_setup = 0 OR p_turnaround = 0 THEN
        RAISE EXCEPTION 'B1_ZERO_DECISION_REQUIRED';
    END IF;
    IF p_start IS NULL OR p_end IS NULL
       OR NOT pg_catalog.isfinite(p_start) OR NOT pg_catalog.isfinite(p_end)
       OR p_start >= p_end THEN
        RAISE EXCEPTION 'B1_INVALID_SCHEDULE';
    END IF;
    occupied_start := p_start - p_setup * interval '1 minute';
    occupied_end := p_end + p_turnaround * interval '1 minute';
    IF occupied_start < lower_bound OR occupied_end > upper_bound THEN
        RAISE EXCEPTION 'B1_DATETIME_OUTSIDE_COMMON_SUPPORTED_RANGE';
    END IF;
    RETURN pg_catalog.tstzrange(occupied_start, occupied_end, '[)');
END
$function$
;
ALTER FUNCTION public.b1_occupied_period(timestamp with time zone,timestamp with time zone,integer,integer) OWNER TO b1_venue_buffer_executor;

CREATE OR REPLACE FUNCTION public.b1_buffer_conflicts(p_venue_id uuid, p_setup integer, p_turnaround integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'pg_catalog', 'pg_temp'
 SET "TimeZone" TO 'UTC'
AS $function$
DECLARE
    blockers jsonb;
    result jsonb;
BEGIN
    SELECT COALESCE(pg_catalog.jsonb_agg(q.item ORDER BY q.item::text), '[]'::jsonb)
    INTO blockers
    FROM (
        SELECT pg_catalog.jsonb_build_object(
            'booking_id', b.booking_id,
            'reason', CASE
                WHEN b.status IS NULL OR b.status NOT IN (
                    'confirmed','requested','tentative','rejected','cancelled'
                ) THEN 'booking_lifecycle_classification_required'
                ELSE 'confirmed_schedule_unassessable' END
        ) AS item
        FROM public.venue_booking b
        WHERE b.venue_id = p_venue_id
          AND (
              b.status IS NULL OR b.status NOT IN (
                  'confirmed','requested','tentative','rejected','cancelled'
              )
              OR (b.status = 'confirmed' AND (
                  b.requested_start IS NULL OR b.requested_end IS NULL
                  OR NOT pg_catalog.isfinite(b.requested_start)
                  OR NOT pg_catalog.isfinite(b.requested_end)
                  OR b.requested_start >= b.requested_end
                  OR b.requested_start < timestamptz '0001-01-01 00:00:00+00'
                  OR b.requested_end > timestamptz '9999-12-31 23:59:59.999999+00'
              ))
          )
        UNION ALL
        SELECT pg_catalog.jsonb_build_object(
            'venue_block_id', v.venue_block_id,
            'reason', CASE
                WHEN v.status IS NULL OR v.status NOT IN ('active','cancelled')
                    THEN 'block_lifecycle_classification_required'
                WHEN v.start_datetime IS NULL OR v.end_datetime IS NULL
                    THEN 'active_block_interval_unresolved_under_bounded_scope'
                WHEN NOT pg_catalog.isfinite(v.start_datetime)
                  OR NOT pg_catalog.isfinite(v.end_datetime)
                  OR v.start_datetime >= v.end_datetime
                    THEN 'active_block_bounded_interval_unassessable'
                ELSE 'active_block_outside_common_supported_range' END
        )
        FROM public.venue_block v
        WHERE v.venue_id = p_venue_id
          AND (
              v.status IS NULL OR v.status NOT IN ('active','cancelled')
              OR (v.status = 'active' AND (
                  v.start_datetime IS NULL OR v.end_datetime IS NULL
                  OR NOT pg_catalog.isfinite(v.start_datetime)
                  OR NOT pg_catalog.isfinite(v.end_datetime)
                  OR v.start_datetime >= v.end_datetime
                  OR v.start_datetime < timestamptz '0001-01-01 00:00:00+00'
                  OR v.end_datetime > timestamptz '9999-12-31 23:59:59.999999+00'
              ))
          )
    ) q;
    IF pg_catalog.jsonb_array_length(blockers) > 0 THEN
        RAISE EXCEPTION 'B1_AUTHORITATIVE_OCCUPANCY_UNASSESSABLE'
            USING ERRCODE = 'P0001', DETAIL = blockers::text,
                  HINT = 'Owning workflow must repair/classify authoritative records or resolve bounded-block scope before a new save or activation.';
    END IF;

    -- Evaluate every computable relevant occupancy, even without another pair.
    -- Overflow is a technical assessment error, never a business conflict.
    PERFORM public.b1_occupied_period(
        b.requested_start, b.requested_end, p_setup, p_turnaround
    )
    FROM public.venue_booking b
    WHERE b.venue_id = p_venue_id
      AND b.status IN ('confirmed','requested','tentative')
      AND b.requested_start IS NOT NULL AND b.requested_end IS NOT NULL
      AND pg_catalog.isfinite(b.requested_start)
      AND pg_catalog.isfinite(b.requested_end)
      AND b.requested_start < b.requested_end;

WITH bookings AS MATERIALIZED (
    SELECT b.booking_id, b.event_id, b.status,
           public.b1_occupied_period(
               b.requested_start, b.requested_end, p_setup, p_turnaround
           ) AS occupied
    FROM public.venue_booking b
    WHERE b.venue_id = p_venue_id
      AND b.status IN ('confirmed','requested','tentative')
      AND b.requested_start IS NOT NULL AND b.requested_end IS NOT NULL
      AND pg_catalog.isfinite(b.requested_start)
      AND pg_catalog.isfinite(b.requested_end)
      AND b.requested_start < b.requested_end
),
blocks AS MATERIALIZED (
    SELECT v.venue_block_id,
           pg_catalog.tstzrange(v.start_datetime, v.end_datetime, '[)') AS occupied
    FROM public.venue_block v
    WHERE v.venue_id = p_venue_id AND v.status = 'active'
      AND v.start_datetime IS NOT NULL AND v.end_datetime IS NOT NULL
      AND pg_catalog.isfinite(v.start_datetime)
      AND pg_catalog.isfinite(v.end_datetime)
      AND v.start_datetime < v.end_datetime
),
conflicts AS (
    SELECT pg_catalog.jsonb_build_object(
        'kind', 'booking_booking',
        'booking_id', a.booking_id, 'event_id', a.event_id,
        'other_booking_id', b.booking_id, 'other_event_id', b.event_id,
        'occupied_start', pg_catalog.lower(a.occupied),
        'occupied_end', pg_catalog.upper(a.occupied),
        'other_occupied_start', pg_catalog.lower(b.occupied),
        'other_occupied_end', pg_catalog.upper(b.occupied),
        'overlap_start', pg_catalog.lower(a.occupied * b.occupied),
        'overlap_end', pg_catalog.upper(a.occupied * b.occupied),
        'assessment', CASE
            WHEN a.status = 'confirmed' AND b.status = 'confirmed'
            THEN 'identified' ELSE 'potential_hold_validity_unavailable' END
    ) AS item
    FROM bookings a JOIN bookings b
      ON a.booking_id < b.booking_id AND a.occupied && b.occupied
    UNION ALL
    SELECT pg_catalog.jsonb_build_object(
        'kind', 'booking_block',
        'booking_id', a.booking_id, 'event_id', a.event_id,
        'venue_block_id', v.venue_block_id,
        'occupied_start', pg_catalog.lower(a.occupied),
        'occupied_end', pg_catalog.upper(a.occupied),
        'other_occupied_start', pg_catalog.lower(v.occupied),
        'other_occupied_end', pg_catalog.upper(v.occupied),
        'overlap_start', pg_catalog.lower(a.occupied * v.occupied),
        'overlap_end', pg_catalog.upper(a.occupied * v.occupied),
        'assessment', CASE WHEN a.status = 'confirmed'
            THEN 'identified' ELSE 'potential_hold_validity_unavailable' END
    ) AS item
    FROM bookings a JOIN blocks v ON a.occupied && v.occupied
)
SELECT COALESCE(pg_catalog.jsonb_agg(item ORDER BY item::text), '[]'::jsonb)
INTO result
FROM conflicts;
    RETURN result;
END
$function$
;
ALTER FUNCTION public.b1_buffer_conflicts(uuid,integer,integer) OWNER TO b1_venue_buffer_executor;

CREATE OR REPLACE FUNCTION public.b1_guard_venue_buffers()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.setup_minutes IS NOT NULL
           OR NEW.turnaround_minutes IS NOT NULL
           OR NEW.buffer_config_revision IS DISTINCT FROM 0::bigint THEN
            RAISE EXCEPTION 'B1_NEW_VENUE_MUST_START_UNCONFIGURED';
        END IF;
        RETURN NEW;
    END IF;

    IF ROW(NEW.setup_minutes, NEW.turnaround_minutes, NEW.buffer_config_revision)
       IS DISTINCT FROM
       ROW(OLD.setup_minutes, OLD.turnaround_minutes, OLD.buffer_config_revision)
    THEN
        IF current_user <> 'b1_venue_buffer_executor' THEN
            RAISE EXCEPTION 'B1_CONTROLLED_SAVE_REQUIRED';
        END IF;
        IF NEW.setup_minutes IS NULL OR NEW.turnaround_minutes IS NULL
           OR ROW(NEW.setup_minutes, NEW.turnaround_minutes)
              IS NOT DISTINCT FROM ROW(OLD.setup_minutes, OLD.turnaround_minutes)
        THEN
            RAISE EXCEPTION 'B1_INVALID_CONTROLLED_CHANGE';
        END IF;
        IF OLD.buffer_config_revision = 9223372036854775807::bigint THEN
            RAISE EXCEPTION 'B1_REVISION_EXHAUSTED';
        END IF;
        IF NEW.buffer_config_revision IS DISTINCT FROM OLD.buffer_config_revision + 1
        THEN
            RAISE EXCEPTION 'B1_INVALID_REVISION_ADVANCE';
        END IF;
    END IF;
    RETURN NEW;
END
$function$
;
ALTER FUNCTION public.b1_guard_venue_buffers() OWNER TO b1_venue_buffer_executor;

CREATE OR REPLACE FUNCTION public.b1_save_venue_buffers(p_venue_id uuid, p_setup_minutes integer, p_turnaround_minutes integer, p_expected_revision bigint, p_operation_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
 SET "TimeZone" TO 'UTC'
AS $function$
DECLARE
    actor uuid := auth.uid();
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
$function$
;
ALTER FUNCTION public.b1_save_venue_buffers(uuid,integer,integer,bigint,uuid) OWNER TO b1_venue_buffer_executor;

CREATE TRIGGER b1_guard_venue_buffer_rows AFTER INSERT OR UPDATE ON venue FOR EACH ROW EXECUTE FUNCTION b1_guard_venue_buffers();
-- Match the supplied owner-only B1 execution grants. The alternatives migration
-- must preserve these ACLs, rather than making the buffer APIs public.
REVOKE ALL ON FUNCTION b1_occupied_period(timestamptz,timestamptz,integer,integer),
 b1_buffer_conflicts(uuid,integer,integer),b1_guard_venue_buffers(),
 b1_save_venue_buffers(uuid,integer,integer,bigint,uuid) FROM PUBLIC,anon,authenticated;
