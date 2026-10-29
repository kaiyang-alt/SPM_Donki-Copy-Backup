-- Local-only integration regression for the agreed approved -> confirmed handoff.
-- Load equipment_proposals_fixture.sql, equipment-acceptance-draft.sql and
-- equipment-proposals-migration.sql first. Never run fixtures in Supabase.
CREATE TABLE public.event_action_log(action_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 event_id uuid REFERENCES public.event,actor_id uuid REFERENCES public.profile,
 action_type text,details text,old_status text,new_status text,created_at timestamptz);
ALTER TABLE public.event_action_log ENABLE ROW LEVEL SECURITY;
GRANT SELECT,INSERT ON public.event_action_log TO authenticated;
CREATE POLICY "Assigned coordinators can create review action logs"
 ON public.event_action_log FOR INSERT TO authenticated WITH CHECK (
((actor_id = auth.uid()) AND (EXISTS ( SELECT 1
   FROM user_role
  WHERE ((user_role.user_id = auth.uid()) AND (user_role.role = 'event_coordinator'::text)))) AND (EXISTS ( SELECT 1
   FROM event
  WHERE ((event.event_id = event_action_log.event_id) AND (event.coordinator_id = auth.uid()) AND (((event_action_log.action_type = 'clarification_requested'::text) AND (event_action_log.old_status = ANY (ARRAY['requested'::text, 'changes_requested'::text])) AND (event_action_log.new_status = 'changes_requested'::text) AND (event.status = 'changes_requested'::text)) OR ((event_action_log.action_type = 'event_approved'::text) AND (event_action_log.old_status = ANY (ARRAY['requested'::text, 'changes_requested'::text])) AND (event_action_log.new_status = 'approved'::text) AND (event.status = 'approved'::text)) OR ((event_action_log.action_type = 'event_rejected'::text) AND (event_action_log.old_status = ANY (ARRAY['requested'::text, 'changes_requested'::text])) AND (event_action_log.new_status = 'rejected'::text) AND (event.status = 'rejected'::text))))))));
-- Both the initial application and retry must preserve the inspected policy.
\ir ../docs/database/coordinator-review-planning-patch.sql
\ir ../docs/database/coordinator-review-planning-patch.sql
BEGIN;
SELECT public.test_equipment_setup();
INSERT INTO public.profile(user_id,name) VALUES('00000000-0000-0000-0000-000000000005','Coordinator');
INSERT INTO public.user_role VALUES('00000000-0000-0000-0000-000000000005','event_coordinator');
UPDATE public.event SET coordinator_id='00000000-0000-0000-0000-000000000005',status='planning';
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000005',true);
-- Current assigned coordinator approves and can record the real old status.
UPDATE public.event SET status='approved' WHERE event_id='30000000-0000-0000-0000-000000000001';
INSERT INTO public.event_action_log(event_id,actor_id,action_type,old_status,new_status,details)
VALUES('30000000-0000-0000-0000-000000000001',auth.uid(),'event_approved','planning','approved','Ready for resource booking');
-- Planning is not resource approval, even though a confirmed venue exists.
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
DO $$BEGIN
 BEGIN
  PERFORM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000002',
   '10000000-0000-0000-0000-000000000001',1,'2026-11-20 12:30+08','2026-11-20 14:00+08');
  RAISE EXCEPTION 'Planning event bypassed initial approval';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'Equipment proposal is not eligible' THEN RAISE; END IF;
 END;
END;$$;
-- Approval makes equipment visible without an existing reservation.
DO $$BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.event WHERE event_id='30000000-0000-0000-0000-000000000001') THEN
  RAISE EXCEPTION 'Approved organiser requirements are hidden';
 END IF;
END;$$;
DO $$DECLARE proposal uuid; BEGIN
 SELECT reservation_id INTO proposal FROM public.propose_equipment_quantity(
  '30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',1,
  '2026-11-20 09:00+08','2026-11-20 12:00+08');
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
 PERFORM public.agree_equipment_proposal(proposal,1);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 IF public.cs_equipment_request_available(proposal)<>5 THEN RAISE EXCEPTION 'Availability failed after approval'; END IF;
 PERFORM public.accept_equipment_request(proposal);
 IF (SELECT status FROM public.event WHERE event_id='30000000-0000-0000-0000-000000000001')<>'approved' THEN
  RAISE EXCEPTION 'Equipment acceptance changed the event status';
 END IF;
END;$$;
-- Audit permission remains assigned-coordinator-only, with matching event state.
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
DO $$BEGIN
 BEGIN
  INSERT INTO public.event_action_log(event_id,actor_id,action_type,old_status,new_status)
  VALUES('30000000-0000-0000-0000-000000000001',auth.uid(),'event_approved','planning','approved');
  RAISE EXCEPTION 'Organiser forged Coordinator approval';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END;$$;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000005',true);
DO $$BEGIN
 BEGIN
  INSERT INTO public.event_action_log(event_id,actor_id,action_type,old_status,new_status)
  VALUES('30000000-0000-0000-0000-000000000001',auth.uid(),'event_rejected','planning','rejected');
  RAISE EXCEPTION 'Mismatched event status was accepted';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END;$$;
UPDATE public.event SET status='confirmed' WHERE event_id='30000000-0000-0000-0000-000000000001' AND status='approved';
ROLLBACK;
\echo 'PASS: planning review audit, approved equipment handoff, consent, reservation, final confirmation and audit restrictions'
