-- Organiser -> Coordinator initial approval -> Technical Support inbox.
-- Planning/confirmed events only; final event confirmation remains Coordinator-owned.
-- No schema/status/INSERT/UPDATE changes; does not create equipment proposals.
-- Run BEGIN through COMMIT as the existing policy owner.
BEGIN;
DO $policy$
BEGIN
  IF NOT EXISTS(SELECT 1 FROM pg_policy WHERE polrelid='public.event'::regclass
                AND polname='Technical support can review equipment requirements') THEN
    CREATE POLICY "Technical support can review equipment requirements" ON public.event
      FOR SELECT TO authenticated USING (false);
  END IF;
END;
$policy$;
ALTER POLICY "Technical support can review equipment requirements" ON public.event
  TO authenticated USING (
    status IN ('planning','confirmed')
    AND (technical_support_required IS TRUE OR nullif(btrim(technical_requirements),'') IS NOT NULL)
    AND EXISTS (SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='technical_support')
  );
COMMIT;
