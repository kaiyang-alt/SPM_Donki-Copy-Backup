-- AC4: approved events must be available to Technical Support for equipment work.
-- This patch changes only the equipment workflow's event-status eligibility.
-- It is safe to rerun: already-updated functions are left unchanged.
BEGIN;

ALTER POLICY "Technical support can review equipment requirements" ON public.event
  TO authenticated
  USING (
    status IN ('approved', 'confirmed')
    AND (
      technical_support_required IS TRUE
      OR nullif(btrim(technical_requirements), '') IS NOT NULL
    )
    AND EXISTS (
      SELECT 1
      FROM public.user_role
      WHERE user_id = auth.uid()
        AND role = 'technical_support'
    )
  );

DO $patch$
DECLARE
  function_signature text;
  function_definition text;
  updated_definition text;
BEGIN
  FOREACH function_signature IN ARRAY ARRAY[
    'public.propose_equipment_quantity(uuid,uuid,integer,timestamptz,timestamptz,uuid,bigint)',
    'public.cs_equipment_acceptance_guard()',
    'public.cs_equipment_request_available(uuid)'
  ]
  LOOP
    SELECT pg_get_functiondef(to_regprocedure(function_signature))
      INTO function_definition;

    IF function_definition IS NULL THEN
      RAISE EXCEPTION 'Required equipment function is missing: %', function_signature;
    END IF;

    updated_definition := replace(
      function_definition,
      '''planning'',''confirmed''',
      '''approved'',''confirmed'''
    );

    IF updated_definition = function_definition
       AND position('''approved'',''confirmed''' IN function_definition) = 0 THEN
      RAISE EXCEPTION
        'Expected equipment eligibility rule was not found in %',
        function_signature;
    END IF;

    IF updated_definition <> function_definition THEN
      EXECUTE updated_definition;
    END IF;
  END LOOP;
END;
$patch$;

NOTIFY pgrst, 'reload schema';
COMMIT;
