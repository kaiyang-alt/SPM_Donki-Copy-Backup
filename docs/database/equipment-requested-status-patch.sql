-- REVIEW PATCH: requested -> reserved equipment acceptance (22 October 2026).
-- Prepared from the user-supplied deployed definitions and the local baseline.
-- Not applied or executed against PostgreSQL by this review.
-- Replaces only the acceptance guard and acceptance RPC. Existing triggers
-- continue referencing the same functions. No data, table constraints, RLS,
-- function signatures, or function grants are changed.
-- Equipment pending status is requested; event eligibility stays planning/confirmed.
-- IMPORTANT: this patch does NOT implement venue-availability/transfer checks.
-- It does not make the newly clarified full booking workflow release-ready.
-- After team review, apply as the function owner and deploy matching app changes.
-- Do not rerun equipment-acceptance-draft.sql against the existing deployment.

BEGIN;

-- Abort if this is not the already-inspected deployment.
DO $preflight$
BEGIN
  IF to_regprocedure('public.cs_equipment_acceptance_guard()') IS NULL
     OR to_regprocedure('public.accept_equipment_request(uuid)') IS NULL THEN
    RAISE EXCEPTION 'Expected existing equipment acceptance functions are missing';
  END IF;
END;
$preflight$;

-- Serialize with the existing equipment-write protocol while replacing functions.
SELECT pg_advisory_xact_lock(212, 8401);

CREATE OR REPLACE FUNCTION public.cs_equipment_acceptance_guard()
RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_event_status text;
  v_extra jsonb := '[]'::jsonb;
  v_earlier record;
BEGIN
  IF TG_OP = 'UPDATE' AND OLD.status = 'reserved' AND NEW.status = 'reserved' THEN
    IF ROW(NEW.event_id,NEW.equipment_id,NEW.quantity_requested,
           NEW.start_datetime,NEW.end_datetime,NEW.requested_at,NEW.requested_by)
       IS DISTINCT FROM
       ROW(OLD.event_id,OLD.equipment_id,OLD.quantity_requested,
           OLD.start_datetime,OLD.end_datetime,OLD.requested_at,OLD.requested_by) THEN
      RAISE EXCEPTION 'Accepted reservation details cannot be changed through this workflow';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.status IS DISTINCT FROM 'reserved' THEN RETURN NEW; END IF;
  IF TG_OP = 'INSERT' THEN
    RAISE EXCEPTION 'Accept an existing requested request instead of inserting reserved stock';
  END IF;
  IF OLD.status IS DISTINCT FROM 'requested' THEN
    RAISE EXCEPTION 'Only requested equipment requests can be accepted';
  END IF;
  IF auth.uid() IS NULL OR NOT EXISTS (
    SELECT 1 FROM public.user_role
    WHERE user_id = auth.uid() AND role = 'technical_support'
  ) THEN
    RAISE EXCEPTION 'Technical Support authentication is required' USING ERRCODE = '42501';
  END IF;
  IF ROW(NEW.event_id,NEW.equipment_id,NEW.quantity_requested,
         NEW.start_datetime,NEW.end_datetime,NEW.requested_at,NEW.requested_by)
     IS DISTINCT FROM
     ROW(OLD.event_id,OLD.equipment_id,OLD.quantity_requested,
         OLD.start_datetime,OLD.end_datetime,OLD.requested_at,OLD.requested_by) THEN
    RAISE EXCEPTION 'Acceptance must preserve the original request details';
  END IF;
  IF NEW.quantity_requested IS NULL OR NEW.quantity_requested <= 0
     OR NEW.requested_at IS NULL THEN
    RAISE EXCEPTION 'Requested quantity and request timestamp must be populated';
  END IF;
  SELECT status INTO v_event_status FROM public.event WHERE event_id = NEW.event_id;
  IF NOT FOUND OR v_event_status IS NULL OR v_event_status NOT IN ('planning','confirmed') THEN
    RAISE EXCEPTION 'Event is inaccessible or not eligible for equipment acceptance';
  END IF;

  -- Reject ambiguous timestamp ordering for this equipment pool.
  IF EXISTS (
    SELECT 1 FROM public.equipment_reservation
    WHERE equipment_id = NEW.equipment_id AND status = 'requested'
      AND requested_at IS NULL
  ) OR EXISTS (
    SELECT 1 FROM public.equipment_reservation
    WHERE equipment_id = NEW.equipment_id AND status = 'requested'
      AND requested_at <= NEW.requested_at
    GROUP BY requested_at HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION 'Equal or missing request timestamps need a confirmed priority decision';
  END IF;

  FOR v_earlier IN
    SELECT * FROM public.equipment_reservation
    WHERE equipment_id = NEW.equipment_id AND status = 'requested'
      AND requested_at < NEW.requested_at
    ORDER BY requested_at
  LOOP
    SELECT status INTO v_event_status FROM public.event WHERE event_id = v_earlier.event_id;
    IF NOT FOUND OR v_event_status IS NULL THEN
      RAISE EXCEPTION 'Cannot verify the event for an earlier equipment request';
    END IF;
    IF v_event_status NOT IN ('planning','confirmed') THEN CONTINUE; END IF;
    IF v_earlier.quantity_requested IS NULL OR v_earlier.quantity_requested <= 0 THEN
      RAISE EXCEPTION 'An earlier request has an invalid quantity';
    END IF;
    IF public.cs_equipment_free_quantity(NEW.equipment_id,
         v_earlier.start_datetime,v_earlier.end_datetime,v_extra)
       >= v_earlier.quantity_requested THEN
      v_extra := v_extra || jsonb_build_array(jsonb_build_object(
        's',v_earlier.start_datetime,'e',v_earlier.end_datetime,
        'q',v_earlier.quantity_requested));
    END IF;
  END LOOP;
  IF public.cs_equipment_free_quantity(NEW.equipment_id,
       NEW.start_datetime,NEW.end_datetime,v_extra) < NEW.quantity_requested THEN
    RAISE EXCEPTION 'Equipment unavailable, or stock is required for an earlier request';
  END IF;
  NEW.decided_by := auth.uid();
  NEW.decided_at := clock_timestamp();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.accept_equipment_request(p_reservation_id uuid)
RETURNS public.equipment_reservation
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_request public.equipment_reservation;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS (
    SELECT 1 FROM public.user_role WHERE user_id = auth.uid() AND role = 'technical_support'
  ) THEN
    RAISE EXCEPTION 'Technical Support authentication is required' USING ERRCODE = '42501';
  END IF;
  IF current_setting('transaction_isolation') <> 'read committed' THEN
    RAISE EXCEPTION 'Equipment acceptance requires READ COMMITTED isolation';
  END IF;
  PERFORM pg_advisory_xact_lock(212,8401);
  SELECT * INTO v_request FROM public.equipment_reservation
    WHERE reservation_id = p_reservation_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Equipment request not found or inaccessible'; END IF;
  IF v_request.status = 'reserved' THEN RETURN v_request; END IF; -- retry after success
  IF v_request.status IS DISTINCT FROM 'requested' THEN
    RAISE EXCEPTION 'Only requested equipment requests can be accepted';
  END IF;
  UPDATE public.equipment_reservation SET status = 'reserved'
    WHERE reservation_id = p_reservation_id AND status = 'requested'
    RETURNING * INTO v_request;
  IF NOT FOUND THEN RAISE EXCEPTION 'Request cannot be updated under the current RLS policies'; END IF;
  RETURN v_request;
END;
$$;

COMMIT;
