-- Equipment quantity proposals and organiser agreement, 22 October 2026.
-- LOCAL MIGRATION ARTIFACT: apply only after reviewing local test results.
-- Requires the existing equipment stock/acceptance functions and triggers.
-- Adds no table, reservation status, authentication method or service-role client.
-- Run the complete transaction as the trusted owner of the existing public tables.
-- Do not reapply the earlier status-only patch after this migration.
BEGIN;
SELECT pg_advisory_xact_lock(212,8401);

ALTER TABLE public.equipment_reservation
  ADD COLUMN IF NOT EXISTS quantity_suggested integer,
  ADD COLUMN IF NOT EXISTS suggested_by uuid REFERENCES public.profile(user_id),
  ADD COLUMN IF NOT EXISTS suggested_at timestamptz,
  ADD COLUMN IF NOT EXISTS proposal_version bigint NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS organiser_agreed_version bigint,
  ADD COLUMN IF NOT EXISTS organiser_agreed_by uuid REFERENCES public.profile(user_id),
  ADD COLUMN IF NOT EXISTS organiser_agreed_at timestamptz;

DO $constraints$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.equipment_reservation'::regclass AND conname='cs_equipment_proposal_values') THEN
    ALTER TABLE public.equipment_reservation ADD CONSTRAINT cs_equipment_proposal_values CHECK (
      (quantity_suggested IS NULL OR quantity_suggested > 0) AND proposal_version >= 0
      AND ((organiser_agreed_version IS NULL AND organiser_agreed_by IS NULL AND organiser_agreed_at IS NULL)
        OR (organiser_agreed_version IS NOT NULL AND organiser_agreed_by IS NOT NULL
          AND organiser_agreed_at IS NOT NULL AND organiser_agreed_version = proposal_version
          AND proposal_version > 0 AND quantity_suggested IS NOT NULL))
    );
  END IF;
END;
$constraints$;

-- Coordinator approval moves the event to approved before Technical Support
-- receives requirements. No equipment row is required for this handoff.
DO $policies$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.event'::regclass AND polname='Technical support can review equipment requirements') THEN
    CREATE POLICY "Technical support can review equipment requirements" ON public.event
    FOR SELECT TO authenticated USING (
      (technical_support_required IS TRUE OR nullif(btrim(technical_requirements),'') IS NOT NULL)
      AND status IN ('approved','confirmed')
      AND EXISTS (SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='technical_support')
    );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.equipment_reservation'::regclass AND polname='Organisers can view own equipment proposals') THEN
    CREATE POLICY "Organisers can view own equipment proposals" ON public.equipment_reservation
    FOR SELECT TO authenticated USING (EXISTS (
      SELECT 1 FROM public.event e WHERE e.event_id=equipment_reservation.event_id AND e.organiser_id=auth.uid()
    ));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.equipment_reservation'::regclass AND polname='Organisers can agree own equipment proposals') THEN
    CREATE POLICY "Organisers can agree own equipment proposals" ON public.equipment_reservation
    FOR UPDATE TO authenticated USING (status='requested' AND EXISTS (
      SELECT 1 FROM public.event e WHERE e.event_id=equipment_reservation.event_id AND e.organiser_id=auth.uid()
    )) WITH CHECK (status='requested' AND EXISTS (
      SELECT 1 FROM public.event e WHERE e.event_id=equipment_reservation.event_id AND e.organiser_id=auth.uid()
    ));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.equipment'::regclass AND polname='Organisers can view offered equipment') THEN
    CREATE POLICY "Organisers can view offered equipment" ON public.equipment
    FOR SELECT TO authenticated USING (EXISTS (
      SELECT 1 FROM public.equipment_reservation r JOIN public.event e ON e.event_id=r.event_id
      WHERE r.equipment_id=equipment.equipment_id AND e.organiser_id=auth.uid()
    ));
  END IF;
END;
$policies$;
ALTER POLICY "Technical support can review equipment requirements" ON public.event
  TO authenticated USING (
    status IN ('approved','confirmed')
    AND (technical_support_required IS TRUE OR nullif(btrim(technical_requirements),'') IS NOT NULL)
    AND EXISTS (SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='technical_support')
  );

-- An organiser may change ONLY agreement fields. Other existing UPDATE grants
-- cannot be used to edit the staff offer, status, original quantity or decision.
CREATE OR REPLACE FUNCTION public.cs_equipment_proposal_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public AS $$
DECLARE
  v_organiser uuid;
  v_technical boolean;
  v_changed boolean;
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'Authenticated equipment proposal access is required' USING ERRCODE='42501';
  END IF;
  SELECT organiser_id INTO v_organiser FROM public.event WHERE event_id=NEW.event_id;
  SELECT EXISTS(SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='technical_support') INTO v_technical;
  -- Explicit organiser agreement takes precedence for multi-role users too.
  IF TG_OP='UPDATE' AND ROW(NEW.organiser_agreed_version,NEW.organiser_agreed_by,NEW.organiser_agreed_at)
       IS DISTINCT FROM ROW(OLD.organiser_agreed_version,OLD.organiser_agreed_by,OLD.organiser_agreed_at)
       AND NEW.organiser_agreed_by IS NOT NULL THEN
    IF v_organiser IS DISTINCT FROM auth.uid() OR NOT EXISTS(SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='event_organiser') OR NEW.status IS DISTINCT FROM 'requested'
       OR (to_jsonb(NEW) - ARRAY['organiser_agreed_version','organiser_agreed_by','organiser_agreed_at'])
          IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['organiser_agreed_version','organiser_agreed_by','organiser_agreed_at']) THEN
      RAISE EXCEPTION 'Only the event organiser can agree to this proposal' USING ERRCODE='42501';
    END IF;
    IF NEW.quantity_suggested IS NULL OR NEW.proposal_version <= 0
       OR NEW.organiser_agreed_version IS DISTINCT FROM NEW.proposal_version THEN
      RAISE EXCEPTION 'Equipment proposal changed; reload before continuing';
    END IF;
    NEW.organiser_agreed_by := auth.uid(); NEW.organiser_agreed_at := clock_timestamp();
    RETURN NEW;
  END IF;
  IF NOT v_technical THEN
    -- Preserve existing Coordinator insertion of a plain, unaccepted request.
    IF TG_OP='INSERT' AND NEW.status='requested' AND NEW.quantity_suggested IS NULL
       AND NEW.proposal_version=0 AND NEW.organiser_agreed_by IS NULL THEN RETURN NEW; END IF;
    RAISE EXCEPTION 'Technical Support authentication is required' USING ERRCODE='42501';
  END IF;
  IF TG_OP='UPDATE' AND OLD.status='reserved' THEN
    IF (to_jsonb(NEW) - ARRAY['status','decision_reason'])
       IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['status','decision_reason']) THEN
      RAISE EXCEPTION 'Accepted reservation details cannot be changed through this workflow';
    END IF;
    RETURN NEW;
  END IF;
  IF TG_OP='UPDATE' AND ROW(NEW.event_id,NEW.quantity_requested,NEW.requested_by,NEW.requested_at)
     IS DISTINCT FROM ROW(OLD.event_id,OLD.quantity_requested,OLD.requested_by,OLD.requested_at) THEN
    RAISE EXCEPTION 'Acceptance must preserve the original request details';
  END IF;
  v_changed := TG_OP='INSERT';
  IF TG_OP='UPDATE' THEN
    v_changed := ROW(NEW.quantity_suggested,NEW.equipment_id,NEW.start_datetime,NEW.end_datetime,NEW.technical_requirements)
      IS DISTINCT FROM ROW(OLD.quantity_suggested,OLD.equipment_id,OLD.start_datetime,OLD.end_datetime,OLD.technical_requirements);
  END IF;
  IF v_changed AND NEW.quantity_suggested IS NOT NULL THEN
    IF NEW.status <> 'requested' OR NEW.quantity_suggested <= 0 THEN
      RAISE EXCEPTION 'Equipment proposal is not eligible';
    END IF;
    NEW.proposal_version := CASE WHEN TG_OP='INSERT' THEN 1 ELSE OLD.proposal_version+1 END;
    NEW.suggested_by := auth.uid(); NEW.suggested_at := clock_timestamp();
    NEW.organiser_agreed_version := NULL; NEW.organiser_agreed_by := NULL; NEW.organiser_agreed_at := NULL;
  ELSIF TG_OP='UPDATE' AND ROW(NEW.proposal_version,NEW.suggested_by,NEW.suggested_at,NEW.organiser_agreed_version,NEW.organiser_agreed_by,NEW.organiser_agreed_at)
     IS DISTINCT FROM ROW(OLD.proposal_version,OLD.suggested_by,OLD.suggested_at,OLD.organiser_agreed_version,OLD.organiser_agreed_by,OLD.organiser_agreed_at) THEN
    RAISE EXCEPTION 'Equipment proposal changed; reload before continuing';
  END IF;
  RETURN NEW;
END;
$$;
CREATE OR REPLACE TRIGGER cs_equipment_proposal_check
BEFORE INSERT OR UPDATE ON public.equipment_reservation
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_proposal_guard();

CREATE OR REPLACE FUNCTION public.propose_equipment_quantity(
  p_event_id uuid, p_equipment_id uuid, p_quantity_suggested integer,
  p_start timestamptz, p_end timestamptz,
  p_reservation_id uuid DEFAULT NULL, p_expected_version bigint DEFAULT NULL
) RETURNS public.equipment_reservation LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public AS $$
DECLARE v_row public.equipment_reservation; v_event public.event;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS (SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='technical_support') THEN
    RAISE EXCEPTION 'Technical Support authentication is required' USING ERRCODE='42501';
  END IF;
  IF p_quantity_suggested IS NULL OR p_quantity_suggested <= 0 THEN RAISE EXCEPTION 'A positive suggested quantity is required'; END IF;
  PERFORM pg_advisory_xact_lock(212,8401);
  SELECT * INTO v_event FROM public.event WHERE event_id=p_event_id;
  IF NOT FOUND OR (v_event.status IS NULL OR v_event.status NOT IN ('approved','confirmed')) OR (v_event.technical_support_required IS NOT TRUE AND nullif(btrim(v_event.technical_requirements),'') IS NULL)
     OR NOT EXISTS(SELECT 1 FROM public.equipment WHERE equipment_id=p_equipment_id AND active IS TRUE) THEN
    RAISE EXCEPTION 'Equipment proposal is not eligible';
  END IF;
  IF p_start IS NULL OR p_end IS NULL OR p_start >= p_end THEN RAISE EXCEPTION 'Equipment period must have a start before its end'; END IF;
  IF public.cs_equipment_free_quantity(p_equipment_id,p_start,p_end) < p_quantity_suggested THEN
    RAISE EXCEPTION 'Equipment unavailable, or stock is required for an earlier request';
  END IF;
  IF p_reservation_id IS NULL THEN
    -- A retry must not silently create a second offer for the same event/item.
    IF EXISTS(SELECT 1 FROM public.equipment_reservation WHERE event_id=p_event_id AND equipment_id=p_equipment_id AND status IN ('requested','reserved')) THEN
      RAISE EXCEPTION 'Equipment proposal changed; reload before continuing';
    END IF;
    INSERT INTO public.equipment_reservation(reservation_id,event_id,equipment_id,quantity_requested,
      start_datetime,end_datetime,technical_requirements,status,requested_by,requested_at,quantity_suggested)
    VALUES(gen_random_uuid(),p_event_id,p_equipment_id,NULL,p_start,p_end,v_event.technical_requirements,
      'requested',auth.uid(),clock_timestamp(),p_quantity_suggested) RETURNING * INTO v_row;
  ELSE
    SELECT * INTO v_row FROM public.equipment_reservation WHERE reservation_id=p_reservation_id FOR UPDATE;
    IF NOT FOUND OR v_row.event_id IS DISTINCT FROM p_event_id OR v_row.equipment_id IS DISTINCT FROM p_equipment_id
       OR v_row.status IS DISTINCT FROM 'requested' OR p_expected_version IS DISTINCT FROM v_row.proposal_version THEN
      RAISE EXCEPTION 'Equipment proposal changed; reload before continuing';
    END IF;
    UPDATE public.equipment_reservation SET quantity_suggested=p_quantity_suggested,start_datetime=p_start,
      end_datetime=p_end,technical_requirements=v_event.technical_requirements WHERE reservation_id=p_reservation_id
      RETURNING * INTO v_row;
  END IF;
  RETURN v_row;
END;
$$;

CREATE OR REPLACE FUNCTION public.agree_equipment_proposal(p_reservation_id uuid,p_expected_version bigint)
RETURNS public.equipment_reservation LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public AS $$
DECLARE v_row public.equipment_reservation; v_organiser uuid;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS(SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='event_organiser') THEN
    RAISE EXCEPTION 'Only the event organiser can agree to this proposal' USING ERRCODE='42501';
  END IF;
  PERFORM pg_advisory_xact_lock(212,8401);
  SELECT * INTO v_row FROM public.equipment_reservation WHERE reservation_id=p_reservation_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Equipment request not found or inaccessible'; END IF;
  SELECT organiser_id INTO v_organiser FROM public.event WHERE event_id=v_row.event_id;
  IF v_organiser IS DISTINCT FROM auth.uid() THEN RAISE EXCEPTION 'Only the event organiser can agree to this proposal' USING ERRCODE='42501'; END IF;
  IF v_row.status IS DISTINCT FROM 'requested' OR v_row.quantity_suggested IS NULL OR v_row.proposal_version <= 0
     OR p_expected_version IS DISTINCT FROM v_row.proposal_version THEN
    RAISE EXCEPTION 'Equipment proposal changed; reload before continuing';
  END IF;
  IF v_row.organiser_agreed_version=v_row.proposal_version THEN RETURN v_row; END IF;
  UPDATE public.equipment_reservation SET organiser_agreed_version=proposal_version,
    organiser_agreed_by=auth.uid(),organiser_agreed_at=clock_timestamp()
    WHERE reservation_id=p_reservation_id RETURNING * INTO v_row;
  RETURN v_row;
END;
$$;

-- Exact finite allocation of anonymous physical units across events/maintenance.
-- Each task is one unit. An event may follow another venue only if a continuous
-- free 30-minute interval exists between them; maintenance cannot be used to
-- teleport a unit between venues. Equivalent unit histories are deduplicated.
-- Search exhaustion raises an error instead of reporting unverified availability.
CREATE OR REPLACE FUNCTION public.cs_equipment_fit_tasks(p_tasks jsonb,p_pos integer,p_states jsonb,p_budget integer)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,public AS $$
DECLARE
  v_task jsonb; v_state jsonb; v_next jsonb; v_result jsonb;
  v_seen jsonb := '[]'; v_gap jsonb; v_can_transfer boolean;
  v_i integer; v_remaining integer := p_budget-1;
BEGIN
  IF p_budget <= 0 THEN RAISE EXCEPTION 'Equipment schedule requires manual allocation review'; END IF;
  IF p_pos >= jsonb_array_length(p_tasks) THEN RETURN jsonb_build_object('fits',true,'remaining',v_remaining); END IF;
  IF jsonb_array_length(p_states)=0 THEN RETURN jsonb_build_object('fits',false,'remaining',v_remaining); END IF;
  v_task := p_tasks->p_pos;
  FOR v_i IN 0..jsonb_array_length(p_states)-1 LOOP
    v_state := p_states->v_i;
    IF v_seen @> jsonb_build_array(v_state) THEN CONTINUE; END IF;
    v_seen := v_seen || jsonb_build_array(v_state);
    IF (v_state->>'last_end')::numeric > (v_task->>'s')::numeric THEN CONTINUE; END IF;
    IF v_task->>'kind'='event' THEN
      IF v_state->>'venue' IS NOT NULL AND v_state->>'venue' IS DISTINCT FROM v_task->>'venue' THEN
        v_can_transfer := (v_task->>'s')::numeric-(v_state->>'last_end')::numeric >= 1800;
        FOR v_gap IN SELECT value FROM jsonb_array_elements(v_state->'gaps') LOOP
          IF (v_gap->>1)::numeric-(v_gap->>0)::numeric >= 1800 THEN v_can_transfer := true; END IF;
        END LOOP;
        IF NOT v_can_transfer THEN CONTINUE; END IF;
      END IF;
      v_next := jsonb_build_object('last_end',v_task->'e','venue',v_task->'venue','gaps','[]'::jsonb);
    ELSE
      v_next := jsonb_set(v_state,'{last_end}',v_task->'e');
      IF v_state->>'venue' IS NOT NULL THEN
        v_next := jsonb_set(v_next,'{gaps}',(v_state->'gaps') || jsonb_build_array(jsonb_build_array(v_state->'last_end',v_task->'s')));
      END IF;
    END IF;
    v_result := public.cs_equipment_fit_tasks(p_tasks,p_pos+1,jsonb_set(p_states,ARRAY[v_i::text],v_next),v_remaining);
    v_remaining := (v_result->>'remaining')::integer;
    IF (v_result->>'fits')::boolean THEN RETURN v_result; END IF;
  END LOOP;
  RETURN jsonb_build_object('fits',false,'remaining',v_remaining);
END;
$$;
REVOKE ALL ON FUNCTION public.cs_equipment_fit_tasks(jsonb,integer,jsonb,integer) FROM PUBLIC,anon,authenticated;

-- Narrow read-only definer checker: authoritative stock/venue visibility without
-- exposing unrelated booking details or widening table SELECT to every role.
-- Must be owned by the trusted table owner, with no caller-controlled user ID.
CREATE OR REPLACE FUNCTION public.cs_equipment_schedule_fits(p_equipment_id uuid,p_extra jsonb DEFAULT '[]')
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
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
    SELECT count(*) INTO v_count FROM public.venue_booking WHERE event_id=v_row.event_id AND status IN ('requested','tentative','confirmed');
    SELECT * INTO v_booking FROM public.venue_booking WHERE event_id=v_row.event_id AND status='confirmed';
    IF v_count<>1 OR NOT FOUND OR v_booking.venue_id IS NULL THEN
      RAISE EXCEPTION 'Exactly one confirmed venue booking is required';
    END IF;
    IF v_booking.requested_start IS DISTINCT FROM v_row.s OR v_booking.requested_end IS DISTINCT FROM v_row.e THEN
      RAISE EXCEPTION 'Equipment proposal period must match the confirmed venue booking';
    END IF;
    IF EXISTS(SELECT 1 FROM public.venue_booking b WHERE b.venue_id=v_booking.venue_id
        AND (b.status IS NULL OR (b.status IN ('requested','tentative','confirmed') AND (b.requested_start IS NULL OR b.requested_end IS NULL OR b.requested_start>=b.requested_end))))
       OR EXISTS(SELECT 1 FROM public.venue_block b WHERE b.venue_id=v_booking.venue_id
        AND (b.status IS NULL OR (b.status='active' AND (b.start_datetime IS NULL OR b.end_datetime IS NULL OR b.start_datetime>=b.end_datetime)))) THEN
      RAISE EXCEPTION 'Venue commitments contain invalid or ambiguous data';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM public.venue WHERE venue_id=v_booking.venue_id AND active IS TRUE) OR EXISTS(
      SELECT 1 FROM public.venue_booking b WHERE b.venue_id=v_booking.venue_id AND b.booking_id<>v_booking.booking_id
      AND b.status IN ('requested','tentative','confirmed') AND b.requested_start<v_row.e AND b.requested_end>v_row.s
    ) OR EXISTS(
      SELECT 1 FROM public.venue_block b WHERE b.venue_id=v_booking.venue_id AND b.status='active'
      AND b.start_datetime<v_row.e AND b.end_datetime>v_row.s
    ) THEN RAISE EXCEPTION 'Confirmed venue is unavailable for the proposed period'; END IF;
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
$$;
REVOKE ALL ON FUNCTION public.cs_equipment_schedule_fits(uuid,jsonb) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.cs_equipment_schedule_fits(uuid,jsonb) TO authenticated;

CREATE OR REPLACE FUNCTION public.cs_equipment_free_quantity(
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
      AND (coalesce(quantity_suggested,quantity_requested) IS NULL OR coalesce(quantity_suggested,quantity_requested) <= 0
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
           coalesce(quantity_suggested,quantity_requested)::bigint AS q
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

CREATE OR REPLACE FUNCTION public.cs_equipment_acceptance_guard()
RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_event_status text;
  v_extra jsonb := '[]'::jsonb;
  v_proposals jsonb := '[]'::jsonb;
  v_organiser uuid;
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
  IF NEW.quantity_suggested IS NULL OR NEW.quantity_suggested <= 0
     OR NEW.requested_at IS NULL THEN
    RAISE EXCEPTION 'Requested quantity and request timestamp must be populated';
  END IF;
  SELECT status,organiser_id INTO v_event_status,v_organiser FROM public.event WHERE event_id = NEW.event_id;
  IF NEW.organiser_agreed_version IS DISTINCT FROM NEW.proposal_version OR NEW.proposal_version<=0
     OR NEW.organiser_agreed_by IS DISTINCT FROM v_organiser OR NEW.organiser_agreed_at IS NULL THEN
    RAISE EXCEPTION 'Current organiser agreement is required';
  END IF;
  IF NEW.technical_requirements IS DISTINCT FROM (SELECT technical_requirements FROM public.event WHERE event_id=NEW.event_id) THEN
    RAISE EXCEPTION 'Equipment proposal changed; reload before continuing';
  END IF;
  IF NOT FOUND OR v_event_status IS NULL OR v_event_status NOT IN ('approved','confirmed') THEN
    RAISE EXCEPTION 'Event is inaccessible or not eligible for equipment acceptance';
  END IF;

  -- Reject ambiguous timestamp ordering for this equipment pool.
  IF EXISTS (
    SELECT 1 FROM public.equipment_reservation
    WHERE equipment_id = NEW.equipment_id AND status = 'requested' AND proposal_version>0 AND organiser_agreed_version=proposal_version AND organiser_agreed_by IS NOT NULL
      AND requested_at IS NULL
  ) OR EXISTS (
    SELECT 1 FROM public.equipment_reservation
    WHERE equipment_id = NEW.equipment_id AND status = 'requested' AND proposal_version>0 AND organiser_agreed_version=proposal_version AND organiser_agreed_by IS NOT NULL
      AND requested_at <= NEW.requested_at
    GROUP BY requested_at HAVING count(*) > 1
  ) THEN
    RAISE EXCEPTION 'Equal or missing request timestamps need a confirmed priority decision';
  END IF;

  FOR v_earlier IN
    SELECT * FROM public.equipment_reservation
    WHERE equipment_id = NEW.equipment_id AND status = 'requested' AND proposal_version>0 AND organiser_agreed_version=proposal_version AND organiser_agreed_by IS NOT NULL
      AND requested_at < NEW.requested_at
    ORDER BY requested_at
  LOOP
    SELECT status INTO v_event_status FROM public.event WHERE event_id = v_earlier.event_id;
    IF NOT FOUND OR v_event_status IS NULL THEN
      RAISE EXCEPTION 'Cannot verify the event for an earlier equipment request';
    END IF;
    IF v_event_status NOT IN ('approved','confirmed') THEN CONTINUE; END IF;
    IF v_earlier.quantity_suggested IS NULL OR v_earlier.quantity_suggested <= 0 THEN
      RAISE EXCEPTION 'An earlier request has an invalid quantity';
    END IF;
    IF public.cs_equipment_free_quantity(NEW.equipment_id,
         v_earlier.start_datetime,v_earlier.end_datetime,v_extra)
       >= v_earlier.quantity_suggested AND public.cs_equipment_schedule_fits(NEW.equipment_id,v_proposals || jsonb_build_array(to_jsonb(v_earlier))) THEN
      v_proposals := v_proposals || jsonb_build_array(to_jsonb(v_earlier));
      v_extra := v_extra || jsonb_build_array(jsonb_build_object(
        's',v_earlier.start_datetime,'e',v_earlier.end_datetime,
        'q',v_earlier.quantity_suggested));
    END IF;
  END LOOP;
  IF public.cs_equipment_free_quantity(NEW.equipment_id,
       NEW.start_datetime,NEW.end_datetime,v_extra) < NEW.quantity_suggested OR NOT public.cs_equipment_schedule_fits(NEW.equipment_id,v_proposals || jsonb_build_array(to_jsonb(NEW))) THEN
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

CREATE OR REPLACE FUNCTION public.cs_equipment_capacity_guard()
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
  IF NOT public.cs_equipment_schedule_fits(v_id) THEN
    RAISE EXCEPTION 'Equipment stock would be overallocated';
  END IF;
  RETURN NEW;
END;
$$;

-- Venue/event writes use the same lock as equipment acceptance. The definer
-- AFTER trigger returns no records; it only rejects arrangements that invalidate
-- already committed equipment. Existing table RLS still authorises the write.
CREATE OR REPLACE FUNCTION public.cs_equipment_arrangement_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE v_old_event uuid; v_new_event uuid; v_old_venue uuid; v_new_venue uuid; v_id uuid;
BEGIN
  IF TG_TABLE_NAME='event' THEN
    -- Unrelated edits (description, readiness/status metadata) do not alter the
    -- equipment arrangement and must keep their existing caller permissions.
    IF TG_OP='UPDATE' AND ROW(NEW.event_id,NEW.start_datetime,NEW.end_datetime,NEW.technical_requirements)
       IS NOT DISTINCT FROM ROW(OLD.event_id,OLD.start_datetime,OLD.end_datetime,OLD.technical_requirements) THEN
      RETURN NULL;
    END IF;
    IF TG_OP<>'INSERT' THEN v_old_event:=OLD.event_id; END IF;
    IF TG_OP<>'DELETE' THEN v_new_event:=NEW.event_id; END IF;
    IF TG_OP='UPDATE' AND NEW.technical_requirements IS DISTINCT FROM OLD.technical_requirements
       AND EXISTS(SELECT 1 FROM public.equipment_reservation WHERE event_id=NEW.event_id AND status='reserved') THEN
      RAISE EXCEPTION 'Accepted equipment requirements must be reviewed before changing the event';
    END IF;
    IF TG_OP='UPDATE' AND ROW(NEW.start_datetime,NEW.end_datetime) IS DISTINCT FROM ROW(OLD.start_datetime,OLD.end_datetime)
       AND EXISTS(SELECT 1 FROM public.equipment_reservation WHERE event_id=NEW.event_id AND status='reserved') THEN
      RAISE EXCEPTION 'Accepted equipment periods must be reviewed before changing the event';
    END IF;
  ELSIF TG_TABLE_NAME='venue_booking' THEN
    IF TG_OP<>'INSERT' THEN v_old_event:=OLD.event_id; v_old_venue:=OLD.venue_id; END IF;
    IF TG_OP<>'DELETE' THEN v_new_event:=NEW.event_id; v_new_venue:=NEW.venue_id; END IF;
  ELSE
    IF TG_OP<>'INSERT' THEN v_old_venue:=OLD.venue_id; END IF;
    IF TG_OP<>'DELETE' THEN v_new_venue:=NEW.venue_id; END IF;
  END IF;
  FOR v_id IN SELECT DISTINCT r.equipment_id FROM public.equipment_reservation r
    WHERE r.status='reserved' AND (r.event_id IN (v_old_event,v_new_event) OR EXISTS(
      SELECT 1 FROM public.venue_booking b WHERE b.event_id=r.event_id AND b.venue_id IN (v_old_venue,v_new_venue)))
  LOOP
    IF NOT public.cs_equipment_schedule_fits(v_id) THEN RAISE EXCEPTION 'Equipment stock would be overallocated'; END IF;
  END LOOP;
  RETURN NULL;
END;
$$;
CREATE OR REPLACE TRIGGER cs_equipment_event_lock BEFORE INSERT OR UPDATE OR DELETE ON public.event
FOR EACH STATEMENT EXECUTE FUNCTION public.cs_equipment_write_lock();
CREATE OR REPLACE TRIGGER cs_equipment_booking_lock BEFORE INSERT OR UPDATE OR DELETE ON public.venue_booking
FOR EACH STATEMENT EXECUTE FUNCTION public.cs_equipment_write_lock();
CREATE OR REPLACE TRIGGER cs_equipment_venue_block_lock BEFORE INSERT OR UPDATE OR DELETE ON public.venue_block
FOR EACH STATEMENT EXECUTE FUNCTION public.cs_equipment_write_lock();
CREATE OR REPLACE TRIGGER cs_equipment_venue_lock BEFORE INSERT OR UPDATE OR DELETE ON public.venue
FOR EACH STATEMENT EXECUTE FUNCTION public.cs_equipment_write_lock();
CREATE OR REPLACE TRIGGER cs_equipment_event_check AFTER INSERT OR UPDATE OR DELETE ON public.event
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_arrangement_guard();
CREATE OR REPLACE TRIGGER cs_equipment_booking_check AFTER INSERT OR UPDATE OR DELETE ON public.venue_booking
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_arrangement_guard();
CREATE OR REPLACE TRIGGER cs_equipment_venue_block_check AFTER INSERT OR UPDATE OR DELETE ON public.venue_block
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_arrangement_guard();
CREATE OR REPLACE TRIGGER cs_equipment_venue_check AFTER INSERT OR UPDATE OR DELETE ON public.venue
FOR EACH ROW EXECUTE FUNCTION public.cs_equipment_arrangement_guard();

REVOKE ALL ON FUNCTION public.propose_equipment_quantity(uuid,uuid,integer,timestamptz,timestamptz,uuid,bigint) FROM PUBLIC,anon;
REVOKE ALL ON FUNCTION public.agree_equipment_proposal(uuid,bigint) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.propose_equipment_quantity(uuid,uuid,integer,timestamptz,timestamptz,uuid,bigint) TO authenticated;
GRANT EXECUTE ON FUNCTION public.agree_equipment_proposal(uuid,bigint) TO authenticated;
REVOKE ALL ON FUNCTION public.cs_equipment_proposal_guard() FROM PUBLIC,anon;
REVOKE ALL ON FUNCTION public.cs_equipment_arrangement_guard() FROM PUBLIC,anon;

-- Deployment preflight: do not silently grandfather an impossible stock/venue
-- schedule. Legacy reserved rows still use their original quantity, without
-- fabricating organiser agreement. Resolve invalid arrangements before retrying.
DO $validate$
DECLARE v_id uuid;
BEGIN
  FOR v_id IN SELECT DISTINCT equipment_id FROM public.equipment_reservation WHERE status='reserved' LOOP
    IF NOT public.cs_equipment_schedule_fits(v_id) THEN RAISE EXCEPTION 'Existing equipment schedule requires review before migration'; END IF;
  END LOOP;
END;
$validate$;
-- Venue-aware displayed quantity uses the same exact allocator as acceptance.
CREATE OR REPLACE FUNCTION public.cs_equipment_request_available(p_reservation_id uuid)
RETURNS bigint LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $$
DECLARE v_row public.equipment_reservation; v_prior record;
  v_extra jsonb := '[]'; v_timeline jsonb := '[]'; v_candidate jsonb;
  v_low bigint := 0; v_high bigint; v_mid bigint;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS(SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='technical_support') THEN
    RAISE EXCEPTION 'Technical Support authentication is required' USING ERRCODE='42501';
  END IF;
  SELECT * INTO v_row FROM public.equipment_reservation WHERE reservation_id=p_reservation_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Equipment request not found or inaccessible'; END IF;
  IF v_row.status IS DISTINCT FROM 'requested' OR v_row.quantity_suggested IS NULL THEN RAISE EXCEPTION 'Equipment proposal is not eligible'; END IF;
  FOR v_prior IN SELECT r.* FROM public.equipment_reservation r JOIN public.event e ON e.event_id=r.event_id
    WHERE r.equipment_id=v_row.equipment_id AND r.status='requested' AND r.requested_at<v_row.requested_at
      AND r.proposal_version>0 AND r.organiser_agreed_version=r.proposal_version
      AND r.organiser_agreed_by=e.organiser_id AND e.status IN ('approved','confirmed') ORDER BY r.requested_at
  LOOP
    IF public.cs_equipment_free_quantity(v_row.equipment_id,v_prior.start_datetime,v_prior.end_datetime,v_timeline)>=v_prior.quantity_suggested
       AND public.cs_equipment_schedule_fits(v_row.equipment_id,v_extra || jsonb_build_array(to_jsonb(v_prior))) THEN
      v_extra := v_extra || jsonb_build_array(to_jsonb(v_prior));
      v_timeline := v_timeline || jsonb_build_array(jsonb_build_object('s',v_prior.start_datetime,'e',v_prior.end_datetime,'q',v_prior.quantity_suggested));
    END IF;
  END LOOP;
  v_high := greatest(0,public.cs_equipment_free_quantity(v_row.equipment_id,v_row.start_datetime,v_row.end_datetime,v_timeline));
  WHILE v_low<v_high LOOP
    v_mid := (v_low+v_high+1)/2;
    v_candidate := to_jsonb(v_row) || jsonb_build_object('quantity_suggested',v_mid);
    IF public.cs_equipment_schedule_fits(v_row.equipment_id,v_extra || jsonb_build_array(v_candidate)) THEN v_low:=v_mid;
    ELSE v_high:=v_mid-1; END IF;
  END LOOP;
  RETURN v_low;
END;
$$;
REVOKE ALL ON FUNCTION public.cs_equipment_request_available(uuid) FROM PUBLIC,anon;
GRANT EXECUTE ON FUNCTION public.cs_equipment_request_available(uuid) TO authenticated;

NOTIFY pgrst, 'reload schema';
COMMIT;
