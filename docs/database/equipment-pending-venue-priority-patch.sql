-- Apply after equipment-proposals-migration.sql to an existing deployment.
-- Skips only earlier pending proposals without a confirmed venue. The candidate
-- and reserved stock still undergo the full consent/venue/stock/transfer checks.
-- Replaces only the two inspected loop fragments, preserving owners and ACLs.
BEGIN;
SET LOCAL statement_timeout = '60s';
SELECT pg_advisory_xact_lock(212,8401);

DO $patch$
DECLARE
  target record;
  definition text;
  insertion text;
BEGIN
  FOR target IN SELECT * FROM (VALUES
    ('public.cs_equipment_acceptance_guard()', 'v_earlier',
      '    IF public.cs_equipment_free_quantity(NEW.equipment_id,'),
    ('public.cs_equipment_request_available(uuid)', 'v_prior',
      '    IF public.cs_equipment_free_quantity(v_row.equipment_id,v_prior.start_datetime,v_prior.end_datetime,v_timeline)>=v_prior.quantity_suggested')
  ) AS targets(signature, variable_name, anchor)
  LOOP
    definition := pg_get_functiondef(target.signature::regprocedure);
    insertion := format($guard$    -- Unconfirmed proposals cannot claim provisional equipment stock.
    IF NOT EXISTS (SELECT 1 FROM public.venue_booking
      WHERE event_id = %s.event_id AND status = 'confirmed') THEN
      CONTINUE;
    END IF;
$guard$, target.variable_name);
    IF position(insertion || target.anchor IN definition) > 0 THEN
      CONTINUE;
    END IF;
    IF (length(definition) - length(replace(definition, target.anchor, '')))
        / length(target.anchor) <> 1 THEN
      RAISE EXCEPTION 'Unexpected definition for %; inspect before applying patch', target.signature;
    END IF;
    EXECUTE replace(definition, target.anchor, insertion || target.anchor);
  END LOOP;
END;
$patch$;

NOTIFY pgrst, 'reload schema';
COMMIT;

-- Expect two rows with skips_unconfirmed_prior_proposals = true.
SELECT oid::regprocedure AS function_name,
  position('Unconfirmed proposals cannot claim provisional equipment stock.' IN prosrc)>0
    AS skips_unconfirmed_prior_proposals
FROM pg_proc
WHERE oid IN ('public.cs_equipment_acceptance_guard()'::regprocedure,
              'public.cs_equipment_request_available(uuid)'::regprocedure);
