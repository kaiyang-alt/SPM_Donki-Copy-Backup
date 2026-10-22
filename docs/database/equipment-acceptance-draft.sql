-- REVIEW DRAFT. Not applied to Supabase and not verified against live RLS.
-- Pending equipment status aligned to requested by user decision, 22 October 2026.
-- This stock-only baseline does not enforce venue availability or transfer gaps.
-- Assumptions requiring team agreement:
-- active unavailability consumes stock; cancelled does not; NULL is an error.
-- Earlier feasible equipment requests in requested status have priority, with provisional allocation
-- used only for checking priority (their stored status is not changed).
-- Equal/missing request timestamps require manual clarification, not a guessed tie-break.
-- All Technical Support callers must see ALL reservations/unavailability for a pool
-- and the events linked to pending requests. SECURITY INVOKER preserves existing RLS.
-- Stock writes use a global transaction advisory lock: simple, but serializes all pools.
-- READ COMMITTED is required for fresh reads after waiting for the lock.

BEGIN;

CREATE FUNCTION public.cs_equipment_write_lock()
RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF current_setting('transaction_isolation') <> 'read committed' THEN
    RAISE EXCEPTION 'Equipment writes require READ COMMITTED isolation';
  END IF;
  PERFORM pg_advisory_xact_lock(212, 8401);
  RETURN NULL; -- statement trigger
END;
$$;

-- Returns the minimum free quantity over a half-open interval. Extra records
-- represent provisional earlier-request allocations, never database writes.
CREATE FUNCTION public.cs_equipment_free_quantity(
  p_equipment_id uuid, p_start timestamptz, p_end timestamptz,
  p_extra jsonb DEFAULT '[]'::jsonb
)
RETURNS bigint
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_total integer;
  v_peak bigint;
BEGIN
  IF p_start IS NULL OR p_end IS NULL OR p_start >= p_end THEN
    RAISE EXCEPTION 'Equipment period must have a start before its end';
  END IF;
  SELECT total_quantity INTO v_total FROM public.equipment
    WHERE equipment_id = p_equipment_id;
  IF NOT FOUND OR v_total IS NULL OR v_total < 0 THEN
    RAISE EXCEPTION 'Equipment stock is missing, inaccessible, or invalid';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.equipment_reservation
    WHERE equipment_id = p_equipment_id AND status = 'reserved'
      AND (quantity_requested IS NULL OR quantity_requested <= 0
        OR start_datetime IS NULL OR end_datetime IS NULL
        OR start_datetime >= end_datetime)
  ) OR EXISTS (
    SELECT 1 FROM public.equipment_unavailability
    WHERE equipment_id = p_equipment_id
      AND (status IS NULL OR status NOT IN ('active','cancelled')
        OR (status = 'active' AND (quantity_unavailable IS NULL
          OR quantity_unavailable <= 0 OR start_datetime IS NULL
          OR end_datetime IS NULL OR start_datetime >= end_datetime)))
  ) THEN
    RAISE EXCEPTION 'Equipment commitments contain invalid or ambiguous data';
  END IF;

  WITH commitments AS (
    SELECT start_datetime AS s, end_datetime AS e,
           quantity_requested::bigint AS q
    FROM public.equipment_reservation
    WHERE equipment_id = p_equipment_id AND status = 'reserved'
    UNION ALL
    SELECT start_datetime, end_datetime, quantity_unavailable::bigint
    FROM public.equipment_unavailability
    WHERE equipment_id = p_equipment_id AND status = 'active'
    UNION ALL
    SELECT x.s, x.e, x.q FROM jsonb_to_recordset(p_extra)
      AS x(s timestamptz, e timestamptz, q bigint)
  ), changes AS (
    SELECT greatest(s,p_start) AS t, q AS delta
      FROM commitments WHERE s < p_end AND e > p_start
    UNION ALL
    SELECT least(e,p_end), -q
      FROM commitments WHERE s < p_end AND e > p_start
  ), grouped AS (
    SELECT t, sum(delta) AS delta FROM changes GROUP BY t
  ), usage AS (
    SELECT t, sum(delta) OVER (ORDER BY t) AS quantity FROM grouped
  )
  SELECT coalesce(max(quantity),0)::bigint INTO v_peak
    FROM usage WHERE t < p_end;
  RETURN v_total::bigint - v_peak;
END;
$$;

-- Runs for every direct or RPC transition to reserved, preventing bypass of
-- the acceptance checks through ordinary table UPDATE/INSERT privileges.
CREATE FUNCTION public.cs_equipment_acceptance_guard()
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

-- Validate the complete stock timeline after writes that commit quantities or
-- alter total stock. Pending Coordinator inserts do not need global stock reads.
CREATE FUNCTION public.cs_equipment_capacity_guard()
RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_id uuid;
  v_start timestamptz;
  v_end timestamptz;
BEGIN
  -- Resolve status only on tables that actually have that field. equipment
  -- has no status column; a compound AND is not a field-resolution guard.
  IF TG_TABLE_NAME = 'equipment_reservation' THEN
    IF NEW.status IS DISTINCT FROM 'reserved' THEN RETURN NEW; END IF;
  ELSIF TG_TABLE_NAME = 'equipment_unavailability' THEN
    IF NEW.status = 'cancelled' THEN RETURN NEW; END IF;
    IF NEW.status IS DISTINCT FROM 'active' THEN
      RAISE EXCEPTION 'Unavailability status must be active or cancelled';
    END IF;
  END IF;
  -- Authenticated callers of these capacity-changing writes need the role
  -- whose documented policies expose the full pool. SQL-owner operations
  -- still execute under their normal privileges; no SECURITY DEFINER bypass.
  IF auth.uid() IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.user_role WHERE user_id = auth.uid() AND role = 'technical_support'
  ) THEN
    RAISE EXCEPTION 'Technical Support visibility is required for capacity validation';
  END IF;
  v_id := NEW.equipment_id;
  -- Calling the helper validates total_quantity and all effective records.
  PERFORM public.cs_equipment_free_quantity(v_id,now(),now() + interval '1 second');
  SELECT min(s),max(e) INTO v_start,v_end FROM (
    SELECT start_datetime s,end_datetime e FROM public.equipment_reservation
      WHERE equipment_id = v_id AND status = 'reserved'
    UNION ALL
    SELECT start_datetime,end_datetime FROM public.equipment_unavailability
      WHERE equipment_id = v_id AND status = 'active'
  ) AS periods;
  IF v_start IS NOT NULL AND public.cs_equipment_free_quantity(v_id,v_start,v_end) < 0 THEN
    RAISE EXCEPTION 'Equipment stock would be overallocated';
  END IF;
  RETURN NEW;
END;
$$;

CREATE FUNCTION public.accept_equipment_request(p_reservation_id uuid)
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

CREATE TRIGGER cs_equipment_reservation_lock
BEFORE INSERT OR UPDATE OR DELETE ON public.equipment_reservation
FOR EACH STATEMENT EXECUTE FUNCTION public.cs_equipment_write_lock();
CREATE TRIGGER cs_equipment_unavailability_lock
BEFORE INSERT OR UPDATE OR DELETE ON public.equipment_unavailability
FOR EACH STATEMENT EXECUTE FUNCTION public.cs_equipment_write_lock();
CREATE TRIGGER cs_equipment_catalogue_lock
BEFORE INSERT OR UPDATE OR DELETE ON public.equipment
FOR EACH STATEMENT EXECUTE FUNCTION public.cs_equipment_write_lock();
CREATE TRIGGER cs_equipment_acceptance_check
BEFORE INSERT OR UPDATE ON public.equipment_reservation
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_acceptance_guard();
CREATE TRIGGER cs_equipment_reservation_capacity
AFTER INSERT OR UPDATE ON public.equipment_reservation
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_capacity_guard();
CREATE TRIGGER cs_equipment_unavailability_capacity
AFTER INSERT OR UPDATE ON public.equipment_unavailability
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_capacity_guard();
CREATE TRIGGER cs_equipment_catalogue_capacity
AFTER INSERT OR UPDATE ON public.equipment
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_capacity_guard();

REVOKE ALL ON FUNCTION public.cs_equipment_free_quantity(uuid,timestamptz,timestamptz,jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.accept_equipment_request(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.cs_equipment_write_lock() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.cs_equipment_acceptance_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.cs_equipment_capacity_guard() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.cs_equipment_free_quantity(uuid,timestamptz,timestamptz,jsonb) TO authenticated;
GRANT EXECUTE ON FUNCTION public.accept_equipment_request(uuid) TO authenticated;

COMMIT;
