-- Local-only integration tests. Requires equipment_proposals_fixture.sql,
-- the equipment baseline, and equipment-proposals-migration.sql. Never seed live data.
CREATE OR REPLACE FUNCTION public.test_expect_error(p_sql text,p_message text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 BEGIN EXECUTE p_sql;
 EXCEPTION WHEN OTHERS THEN
   IF position(p_message IN SQLERRM)>0 THEN RETURN; END IF;
   RAISE;
 END;
 RAISE EXCEPTION 'Expected rejection containing: %',p_message;
END; $$;

BEGIN;
SELECT public.test_equipment_setup();
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
DO $$BEGIN
 IF (SELECT count(*) FROM public.event WHERE technical_support_required)<>2 THEN RAISE EXCEPTION 'Missing organiser events before equipment rows'; END IF;
END;$$;
INSERT INTO public.equipment_reservation(reservation_id,event_id,equipment_id,quantity_requested,start_datetime,end_datetime,status,requested_by,requested_at)
VALUES('50000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',5,'2026-11-20 09:00+08','2026-11-20 12:00+08','requested',auth.uid(),clock_timestamp());
SELECT public.propose_equipment_quantity('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',3,'2026-11-20 09:00+08','2026-11-20 12:00+08','50000000-0000-0000-0000-000000000001',0);
DO $$BEGIN
 IF NOT EXISTS(SELECT 1 FROM equipment_reservation WHERE quantity_requested=5 AND quantity_suggested=3 AND status='requested' AND proposal_version=1 AND organiser_agreed_by IS NULL) THEN RAISE EXCEPTION 'Proposal did not preserve original five / offered three'; END IF;
 IF public.cs_equipment_free_quantity('10000000-0000-0000-0000-000000000001','2026-11-20 09:00+08','2026-11-20 12:00+08')<>5 THEN RAISE EXCEPTION 'Proposal committed stock'; END IF;
END;$$;
SELECT public.test_expect_error($q$SELECT public.accept_equipment_request('50000000-0000-0000-0000-000000000001')$q$,'Current organiser agreement is required');
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000003',true);
DO $$BEGIN IF EXISTS(SELECT 1 FROM equipment_reservation) THEN RAISE EXCEPTION 'Other organiser can read the offer'; END IF; END;$$;
SELECT public.test_expect_error($q$SELECT public.agree_equipment_proposal('50000000-0000-0000-0000-000000000001',1)$q$,'not found or inaccessible');
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
SELECT public.test_expect_error($q$UPDATE public.equipment_reservation SET quantity_suggested=1 WHERE reservation_id='50000000-0000-0000-0000-000000000001'$q$,'Technical Support authentication is required');
SELECT public.agree_equipment_proposal('50000000-0000-0000-0000-000000000001',1);
SELECT public.agree_equipment_proposal('50000000-0000-0000-0000-000000000001',1); -- idempotent
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
SELECT public.accept_equipment_request('50000000-0000-0000-0000-000000000001');
SELECT public.accept_equipment_request('50000000-0000-0000-0000-000000000001'); -- idempotent
DO $$BEGIN
 IF NOT EXISTS(SELECT 1 FROM equipment_reservation WHERE quantity_requested=5 AND quantity_suggested=3 AND status='reserved') THEN RAISE EXCEPTION 'Accepted wrong quantity'; END IF;
 IF public.cs_equipment_free_quantity('10000000-0000-0000-0000-000000000001','2026-11-20 09:00+08','2026-11-20 12:00+08')<>2 THEN RAISE EXCEPTION 'Stock was not reduced by exactly three'; END IF;
END;$$;
SELECT public.test_expect_error($q$UPDATE public.equipment_reservation SET quantity_suggested=4 WHERE reservation_id='50000000-0000-0000-0000-000000000001'$q$,'Accepted reservation details');
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
UPDATE public.event SET description='Updated event description' WHERE event_id='30000000-0000-0000-0000-000000000001';
DO $$BEGIN IF NOT EXISTS(SELECT 1 FROM event WHERE description='Updated event description') THEN RAISE EXCEPTION 'Unrelated organiser event edit was blocked'; END IF; END;$$;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000004',true);
SELECT public.test_expect_error($q$UPDATE public.venue_booking SET status='cancelled' WHERE booking_id='40000000-0000-0000-0000-000000000001'$q$,'Exactly one confirmed venue booking');
ROLLBACK;
\echo 'PASS: organiser inbox, five/three, consent, stock accounting, ownership, retries, direct writes, venue change guard'

BEGIN;
SELECT public.test_equipment_setup();
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
SELECT public.propose_equipment_quantity('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',3,'2026-11-20 09:00+08','2026-11-20 12:00+08');
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
SELECT public.agree_equipment_proposal((SELECT reservation_id FROM equipment_reservation LIMIT 1),1);
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
SELECT public.propose_equipment_quantity('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',2,'2026-11-20 09:00+08','2026-11-20 12:00+08',(SELECT reservation_id FROM equipment_reservation LIMIT 1),1);
DO $$BEGIN IF NOT EXISTS(SELECT 1 FROM equipment_reservation WHERE proposal_version=2 AND organiser_agreed_by IS NULL AND organiser_agreed_version IS NULL AND status='requested') THEN RAISE EXCEPTION 'Revision retained stale agreement'; END IF; END;$$;
SELECT public.test_expect_error($q$SELECT public.accept_equipment_request((SELECT reservation_id FROM equipment_reservation LIMIT 1))$q$,'Current organiser agreement');
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
SELECT public.test_expect_error($q$SELECT public.agree_equipment_proposal((SELECT reservation_id FROM equipment_reservation LIMIT 1),1)$q$,'Equipment proposal changed');
ROLLBACK;
\echo 'PASS: revision invalidation and stale agreement prevention'

-- Directly exercise the same allocator used by BEFORE/AFTER guards. The proposed
-- extra rows stand for the candidate requests, never database commitments.
BEGIN;
SELECT public.test_equipment_setup(1,'12:29',false);
DO $$DECLARE x jsonb; BEGIN
 x := '[{"event_id":"30000000-0000-0000-0000-000000000001","start_datetime":"2026-11-20T09:00:00+08:00","end_datetime":"2026-11-20T12:00:00+08:00","quantity_suggested":1},{"event_id":"30000000-0000-0000-0000-000000000002","start_datetime":"2026-11-20T12:29:00+08:00","end_datetime":"2026-11-20T14:00:00+08:00","quantity_suggested":1}]';
 IF public.cs_equipment_schedule_fits('10000000-0000-0000-0000-000000000001',x) THEN RAISE EXCEPTION 'Allowed a 29-minute transfer'; END IF;
 IF public.cs_equipment_schedule_fits('10000000-0000-0000-0000-000000000001',jsonb_build_array(x->1,x->0)) THEN RAISE EXCEPTION 'Reverse order bypassed transfer'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: different venues in the same building require 30 minutes, independent of acceptance order'
BEGIN;
SELECT public.test_equipment_setup(1,'12:30',false);
DO $$BEGIN
 IF NOT public.cs_equipment_schedule_fits('10000000-0000-0000-0000-000000000001','[{"event_id":"30000000-0000-0000-0000-000000000001","start_datetime":"2026-11-20T09:00:00+08:00","end_datetime":"2026-11-20T12:00:00+08:00","quantity_suggested":1},{"event_id":"30000000-0000-0000-0000-000000000002","start_datetime":"2026-11-20T12:30:00+08:00","end_datetime":"2026-11-20T14:00:00+08:00","quantity_suggested":1}]') THEN RAISE EXCEPTION 'Rejected exact 30-minute transfer'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: exact 30-minute transfer allowed'
BEGIN;
SELECT public.test_equipment_setup(1,'12:00',true);
DO $$BEGIN
 IF NOT public.cs_equipment_schedule_fits('10000000-0000-0000-0000-000000000001','[{"event_id":"30000000-0000-0000-0000-000000000001","start_datetime":"2026-11-20T09:00:00+08:00","end_datetime":"2026-11-20T12:00:00+08:00","quantity_suggested":1},{"event_id":"30000000-0000-0000-0000-000000000002","start_datetime":"2026-11-20T12:00:00+08:00","end_datetime":"2026-11-20T14:00:00+08:00","quantity_suggested":1}]') THEN RAISE EXCEPTION 'Rejected same-venue immediate reuse'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: same venue immediate reuse allowed'
BEGIN;
SELECT public.test_equipment_setup(2,'12:00',false);
DO $$BEGIN
 IF NOT public.cs_equipment_schedule_fits('10000000-0000-0000-0000-000000000001','[{"event_id":"30000000-0000-0000-0000-000000000001","start_datetime":"2026-11-20T09:00:00+08:00","end_datetime":"2026-11-20T12:00:00+08:00","quantity_suggested":1},{"event_id":"30000000-0000-0000-0000-000000000002","start_datetime":"2026-11-20T12:00:00+08:00","end_datetime":"2026-11-20T14:00:00+08:00","quantity_suggested":1}]') THEN RAISE EXCEPTION 'Blocked independent spare unit'; END IF;
END;$$;
INSERT INTO equipment_unavailability(equipment_id,quantity_unavailable,start_datetime,end_datetime,status) VALUES('10000000-0000-0000-0000-000000000001',1,'2026-11-20 11:00+08','2026-11-20 13:00+08','active');
DO $$BEGIN
 IF public.cs_equipment_schedule_fits('10000000-0000-0000-0000-000000000001','[{"event_id":"30000000-0000-0000-0000-000000000001","start_datetime":"2026-11-20T09:00:00+08:00","end_datetime":"2026-11-20T12:00:00+08:00","quantity_suggested":1},{"event_id":"30000000-0000-0000-0000-000000000002","start_datetime":"2026-11-20T12:00:00+08:00","end_datetime":"2026-11-20T14:00:00+08:00","quantity_suggested":1}]') THEN RAISE EXCEPTION 'Maintenance did not remove the spare unit'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: pooled spare quantities and maintenance'

DO $$BEGIN
 IF has_function_privilege('anon','public.propose_equipment_quantity(uuid,uuid,integer,timestamptz,timestamptz,uuid,bigint)','EXECUTE')
 OR has_function_privilege('authenticated','public.cs_equipment_fit_tasks(jsonb,integer,jsonb,integer)','EXECUTE') THEN RAISE EXCEPTION 'Unexpected public allocator/proposal privileges'; END IF;
END;$$;
\echo 'PASS: private allocator and authenticated-only proposal RPC grants'

BEGIN;
SELECT public.test_equipment_setup();
UPDATE event SET status='requested',technical_support_required=false WHERE event_id='30000000-0000-0000-0000-000000000001';
UPDATE event SET status='draft' WHERE event_id='30000000-0000-0000-0000-000000000002';
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
DO $$BEGIN
 IF EXISTS(SELECT 1 FROM event WHERE status IN ('requested','changes_requested','draft')) THEN RAISE EXCEPTION 'Technical inbox bypassed Coordinator approval'; END IF;
 IF EXISTS(SELECT 1 FROM event WHERE status='draft') THEN RAISE EXCEPTION 'Technical Support can see an organiser draft'; END IF;
 IF EXISTS(SELECT 1 FROM equipment_reservation) THEN RAISE EXCEPTION 'Test incorrectly depended on an equipment row'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: requirements await Coordinator approval before Technical Support visibility'

-- Full proposal/consent/acceptance path: start 12:29, same venue False, reverse False.
BEGIN;
SELECT public.test_equipment_setup(1,'12:29',false);
SET LOCAL ROLE authenticated;
DO $$DECLARE a uuid; b uuid; BEGIN
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 SELECT reservation_id INTO a FROM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',1,'2026-11-20 09:00+08','2026-11-20 12:00+08');
 SELECT reservation_id INTO b FROM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000001',1,'2026-11-20 12:29+08','2026-11-20 14:00+08');
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
 PERFORM public.agree_equipment_proposal(b,1);
 PERFORM public.agree_equipment_proposal(a,1);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 PERFORM public.test_expect_error(format('SELECT public.accept_equipment_request(%L)',b),'Equipment unavailable, or stock is required for an earlier request');
 PERFORM public.accept_equipment_request(a);
 IF public.cs_equipment_request_available(b)<>0 THEN RAISE EXCEPTION 'Display bypassed transfer gap'; END IF;
 PERFORM public.test_expect_error(format('SELECT public.accept_equipment_request(%L)',b),'Equipment unavailable, or stock is required for an earlier request');
 IF (SELECT count(*) FROM equipment_reservation WHERE status='reserved')<>1 THEN RAISE EXCEPTION 'Unexpected final committed quantity'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: final RPC transfer 12:29, same venue False, reverse False'

-- Full proposal/consent/acceptance path: start 12:30, same venue False, reverse False.
BEGIN;
SELECT public.test_equipment_setup(1,'12:30',false);
SET LOCAL ROLE authenticated;
DO $$DECLARE a uuid; b uuid; BEGIN
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 SELECT reservation_id INTO a FROM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',1,'2026-11-20 09:00+08','2026-11-20 12:00+08');
 SELECT reservation_id INTO b FROM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000001',1,'2026-11-20 12:30+08','2026-11-20 14:00+08');
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
 PERFORM public.agree_equipment_proposal(b,1);
 PERFORM public.agree_equipment_proposal(a,1);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 PERFORM public.accept_equipment_request(b);
 PERFORM public.accept_equipment_request(a);
 IF (SELECT count(*) FROM equipment_reservation WHERE status='reserved')<>2 THEN RAISE EXCEPTION 'Unexpected final committed quantity'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: final RPC transfer 12:30, same venue False, reverse False'

-- Full proposal/consent/acceptance path: start 12:00, same venue True, reverse False.
BEGIN;
SELECT public.test_equipment_setup(1,'12:00',true);
SET LOCAL ROLE authenticated;
DO $$DECLARE a uuid; b uuid; BEGIN
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 SELECT reservation_id INTO a FROM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',1,'2026-11-20 09:00+08','2026-11-20 12:00+08');
 SELECT reservation_id INTO b FROM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000001',1,'2026-11-20 12:00+08','2026-11-20 14:00+08');
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
 PERFORM public.agree_equipment_proposal(b,1);
 PERFORM public.agree_equipment_proposal(a,1);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 PERFORM public.accept_equipment_request(b);
 PERFORM public.accept_equipment_request(a);
 IF (SELECT count(*) FROM equipment_reservation WHERE status='reserved')<>2 THEN RAISE EXCEPTION 'Unexpected final committed quantity'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: final RPC transfer 12:00, same venue True, reverse False'

-- Full proposal/consent/acceptance path: start 12:29, same venue False, reverse True.
BEGIN;
SELECT public.test_equipment_setup(1,'12:29',false);
SET LOCAL ROLE authenticated;
DO $$DECLARE a uuid; b uuid; BEGIN
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 SELECT reservation_id INTO a FROM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',1,'2026-11-20 09:00+08','2026-11-20 12:00+08');
 SELECT reservation_id INTO b FROM public.propose_equipment_quantity('30000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000001',1,'2026-11-20 12:29+08','2026-11-20 14:00+08');
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
 PERFORM public.agree_equipment_proposal(b,1);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 PERFORM public.accept_equipment_request(b);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
 PERFORM public.agree_equipment_proposal(a,1);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 PERFORM public.test_expect_error(format('SELECT public.accept_equipment_request(%L)',a),'Equipment unavailable, or stock is required for an earlier request');
 IF (SELECT count(*) FROM equipment_reservation WHERE status='reserved')<>1 THEN RAISE EXCEPTION 'Unexpected final committed quantity'; END IF;
END;$$;
ROLLBACK;
\echo 'PASS: final RPC transfer 12:29, same venue False, reverse True'

-- Regression: an earlier agreed request in 2029 has no confirmed venue;
-- it must not break availability or acceptance for a ready event in 2026.
BEGIN;
SELECT public.test_equipment_setup(1);
DELETE FROM public.venue_booking WHERE event_id='30000000-0000-0000-0000-000000000001';
SET LOCAL ROLE authenticated;
DO $$DECLARE earlier uuid; candidate uuid; BEGIN
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 SELECT reservation_id INTO earlier FROM public.propose_equipment_quantity(
   '30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',1,
   '2029-02-12 09:00+08','2029-02-12 12:00+08');
 SELECT reservation_id INTO candidate FROM public.propose_equipment_quantity(
   '30000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000001',1,
   '2026-11-20 12:30+08','2026-11-20 14:00+08');
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
 PERFORM public.agree_equipment_proposal(earlier,1);
 PERFORM public.agree_equipment_proposal(candidate,1);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 -- Skipping an earlier proposal must not bypass the candidate's own venue rule.
 PERFORM public.test_expect_error(format('SELECT public.cs_equipment_request_available(%L)',earlier),
   'Exactly one confirmed venue booking is required');
 PERFORM public.test_expect_error(format('SELECT public.accept_equipment_request(%L)',earlier),
   'Exactly one confirmed venue booking is required');
 IF public.cs_equipment_request_available(candidate)<>1 THEN
   RAISE EXCEPTION 'Venue-less earlier proposal blocked availability';
 END IF;
 PERFORM public.accept_equipment_request(candidate);
 PERFORM public.accept_equipment_request(candidate);
 IF NOT EXISTS(SELECT 1 FROM public.equipment_reservation
     WHERE reservation_id=candidate AND status='reserved' AND quantity_suggested=1)
   OR NOT EXISTS(SELECT 1 FROM public.equipment_reservation
     WHERE reservation_id=earlier AND status='requested') THEN
   RAISE EXCEPTION 'Acceptance changed the wrong request';
 END IF;
END;$$;
ROLLBACK;
\echo 'PASS: earlier agreed proposal without a venue cannot block a ready event; candidate venue and retry checks preserved'

-- A feasible earlier request still has priority over overlapping later demand.
BEGIN;
SELECT public.test_equipment_setup(1,'10:00',false);
SET LOCAL ROLE authenticated;
DO $$DECLARE earlier uuid; candidate uuid; BEGIN
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 SELECT reservation_id INTO earlier FROM public.propose_equipment_quantity(
   '30000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001',1,
   '2026-11-20 09:00+08','2026-11-20 12:00+08');
 SELECT reservation_id INTO candidate FROM public.propose_equipment_quantity(
   '30000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000001',1,
   '2026-11-20 10:00+08','2026-11-20 14:00+08');
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
 PERFORM public.agree_equipment_proposal(earlier,1);
 PERFORM public.agree_equipment_proposal(candidate,1);
 PERFORM set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
 IF public.cs_equipment_request_available(candidate)<>0 THEN
   RAISE EXCEPTION 'Overlapping candidate bypassed earlier feasible request';
 END IF;
 PERFORM public.test_expect_error(format('SELECT public.accept_equipment_request(%L)',candidate),
   'Equipment unavailable, or stock is required for an earlier request');
 IF EXISTS(SELECT 1 FROM public.equipment_reservation WHERE status='reserved') THEN
   RAISE EXCEPTION 'Failed acceptance committed stock';
 END IF;
END;$$;
ROLLBACK;
\echo 'PASS: earlier feasible overlapping request retains stock priority and failure is atomic'
