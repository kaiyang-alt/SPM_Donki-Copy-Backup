-- Approved shared change for update-equipment-operational-status.
-- Run in the Supabase SQL Editor against the shared project.

BEGIN;

ALTER TABLE public.equipment
  ADD COLUMN IF NOT EXISTS operational_status text;

UPDATE public.equipment
SET operational_status = 'available'
WHERE operational_status IS NULL;

ALTER TABLE public.equipment
  ALTER COLUMN operational_status SET DEFAULT 'available',
  ALTER COLUMN operational_status SET NOT NULL;

DO $constraint$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'public.equipment'::regclass
      AND conname = 'equipment_operational_status_check'
  ) THEN
    ALTER TABLE public.equipment
      ADD CONSTRAINT equipment_operational_status_check
      CHECK (operational_status IN (
        'available', 'damaged', 'under_repair', 'unavailable'
      ));
  END IF;
END;
$constraint$;

CREATE OR REPLACE FUNCTION public.update_equipment_operational_status(
  p_equipment_id uuid,
  p_operational_status text
)
RETURNS public.equipment
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_equipment public.equipment;
BEGIN
  IF auth.uid() IS NULL OR NOT EXISTS (
    SELECT 1
    FROM public.user_role
    WHERE user_id = auth.uid()
      AND role = 'technical_support'
  ) THEN
    RAISE EXCEPTION 'Technical Support authentication is required'
      USING ERRCODE = '42501';
  END IF;

  IF p_operational_status IS NULL OR p_operational_status NOT IN (
    'available', 'damaged', 'under_repair', 'unavailable'
  ) THEN
    RAISE EXCEPTION 'Unsupported equipment operational status'
      USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_equipment
  FROM public.equipment
  WHERE equipment_id = p_equipment_id
  FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Equipment item not found'
      USING ERRCODE = 'P0002';
  END IF;

  UPDATE public.equipment
  SET operational_status = p_operational_status
  WHERE equipment_id = p_equipment_id
  RETURNING * INTO v_equipment;

  RETURN v_equipment;
END;
$$;

REVOKE ALL ON FUNCTION public.update_equipment_operational_status(uuid, text)
  FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.update_equipment_operational_status(uuid, text)
  TO authenticated;

CREATE OR REPLACE FUNCTION public.cs_equipment_operational_status_guard()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF NEW.status IN ('requested', 'reserved')
     AND NOT EXISTS (
       SELECT 1
       FROM public.equipment
       WHERE equipment_id = NEW.equipment_id
         AND active IS TRUE
         AND operational_status = 'available'
     ) THEN
    RAISE EXCEPTION 'Equipment is not operationally available';
  END IF;

  RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.cs_equipment_operational_status_guard()
  FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS cs_equipment_operational_status_guard
  ON public.equipment_reservation;

CREATE TRIGGER cs_equipment_operational_status_guard
BEFORE INSERT OR UPDATE OF equipment_id, status, quantity_suggested,
  start_datetime, end_datetime
ON public.equipment_reservation
FOR EACH ROW
EXECUTE FUNCTION public.cs_equipment_operational_status_guard();

NOTIFY pgrst, 'reload schema';

COMMIT;
