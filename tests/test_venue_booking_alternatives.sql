-- Local PostgreSQL integration tests. NEVER run in Supabase.
-- Load venue_booking_alternatives_fixture.sql and the complete migration first.
-- Each assertion raises on failure; synthetic data is rolled back at the end.
BEGIN;
CREATE FUNCTION pg_temp.check_true(p_ok boolean,p_message text) RETURNS void
LANGUAGE plpgsql AS $$ BEGIN IF p_ok IS DISTINCT FROM true THEN RAISE EXCEPTION '%',p_message; END IF; END; $$;
INSERT INTO profile(user_id,name) VALUES('00000000-0000-0000-0000-000000000005','Coordinator');
INSERT INTO user_role VALUES('00000000-0000-0000-0000-000000000005','event_coordinator');
CREATE POLICY test_coordinator_bookings ON venue_booking FOR SELECT TO authenticated
USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='event_coordinator'));
CREATE POLICY test_coordinator_insert ON venue_booking FOR INSERT TO authenticated
WITH CHECK(requested_by=auth.uid() AND EXISTS(SELECT 1 FROM event WHERE event_id=venue_booking.event_id AND coordinator_id=auth.uid()));
INSERT INTO venue(venue_id,name) VALUES
 ('20000000-0000-0000-0000-000000000001','Room A'),('20000000-0000-0000-0000-000000000002','Room B');
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000004',true);
SELECT b1_save_venue_buffers('20000000-0000-0000-0000-000000000001',15,15,0,gen_random_uuid());
SELECT b1_save_venue_buffers('20000000-0000-0000-0000-000000000002',15,15,0,gen_random_uuid());
SELECT set_config('request.jwt.claim.sub','',true);
INSERT INTO event(event_id,organiser_id,coordinator_id,name,status,technical_support_required,technical_requirements)
SELECT ('30000000-0000-0000-0000-'||lpad(n::text,12,'0'))::uuid,
 '00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000005',
 'Event '||n,'approved',true,'Projector' FROM generate_series(1,4) n;
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000005',true);
INSERT INTO venue_booking(booking_id,event_id,venue_id,requested_start,requested_end,status,setup_layout,requested_by)
VALUES
 ('40000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','2026-11-20 09:00+08','2026-11-20 12:00+08','requested','Theatre',auth.uid()),
 ('40000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002','2026-11-20 13:00+08','2026-11-20 16:00+08','requested','Classroom',auth.uid()),
 ('40000000-0000-0000-0000-000000000003','30000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000001','2026-11-20 10:00+08','2026-11-20 11:00+08','requested','Theatre',auth.uid()),
 ('40000000-0000-0000-0000-000000000004','30000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000001','2026-11-21 09:00+08','2026-11-21 12:00+08','requested','Theatre',auth.uid()),
 ('40000000-0000-0000-0000-000000000005','30000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000002','2026-11-21 13:00+08','2026-11-21 16:00+08','requested','Classroom',auth.uid()),
 ('40000000-0000-0000-0000-000000000006','30000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000002','2026-11-20 12:29+08','2026-11-20 14:00+08','requested','Theatre',auth.uid());
SELECT pg_temp.check_true((SELECT count(*)=2 AND count(DISTINCT setup_layout)=2 FROM venue_booking
 WHERE event_id='30000000-0000-0000-0000-000000000001'),'Alternatives must retain independent layouts');
DO $$ BEGIN
 BEGIN
  PERFORM confirm_venue_booking('40000000-0000-0000-0000-000000000001');
  RAISE EXCEPTION 'Coordinator confirmation unexpectedly succeeded';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END; $$;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000004',true);
UPDATE venue_booking SET status='tentative' WHERE booking_id='40000000-0000-0000-0000-000000000002';
SELECT confirm_venue_booking('40000000-0000-0000-0000-000000000001');
SELECT pg_temp.check_true((SELECT status='cancelled' AND setup_layout='Classroom' FROM venue_booking
 WHERE booking_id='40000000-0000-0000-0000-000000000002'),'Tentative sibling must cancel without losing layout');
SELECT pg_temp.check_true((SELECT status='requested' FROM venue_booking
 WHERE booking_id='40000000-0000-0000-0000-000000000003'),'Other events must remain untouched');
CREATE TEMP TABLE saved_confirmation AS SELECT * FROM venue_booking WHERE booking_id='40000000-0000-0000-0000-000000000001';
SELECT confirm_venue_booking('40000000-0000-0000-0000-000000000001');
SELECT pg_temp.check_true((SELECT to_jsonb(b)=to_jsonb(s) FROM venue_booking b CROSS JOIN saved_confirmation s
 WHERE b.booking_id=s.booking_id),'Confirmation retry must return identical saved audit fields');
DO $$ BEGIN
 BEGIN
  PERFORM confirm_venue_booking('40000000-0000-0000-0000-000000000002');
  RAISE EXCEPTION 'Cancelled alternative unexpectedly confirmed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'Only pending venue requests can be confirmed' THEN RAISE; END IF;
 END;
 BEGIN
  PERFORM confirm_venue_booking('40000000-0000-0000-0000-000000000003');
  RAISE EXCEPTION 'Overlapping pending request unexpectedly confirmed';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'Venue is unavailable for the occupied period' THEN RAISE; END IF;
 END;
END; $$;
SELECT pg_temp.check_true(NOT cs_venue_period_available('20000000-0000-0000-0000-000000000001','2026-11-20 12:29+08','2026-11-20 14:00+08'),'29-minute venue gap must fail');
SELECT pg_temp.check_true(cs_venue_period_available('20000000-0000-0000-0000-000000000001','2026-11-20 12:30+08','2026-11-20 14:00+08'),'30-minute venue gap must pass for 15+15 buffers');
DO $$ BEGIN
 BEGIN
  INSERT INTO venue_block(venue_id,start_datetime,end_datetime,status)
  VALUES('20000000-0000-0000-0000-000000000001','2026-11-20 08:50+08','2026-11-20 08:55+08','active');
  RAISE EXCEPTION 'Block overlapping setup unexpectedly saved';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'Venue block overlaps a confirmed occupied period' THEN RAISE; END IF;
 END;
END; $$;
RESET ROLE;
-- Force cancellation failure and establish that the confirmation rolls back too.
CREATE FUNCTION pg_temp.fail_sibling_cancel() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.event_id='30000000-0000-0000-0000-000000000003' AND NEW.status='cancelled' THEN
 RAISE EXCEPTION 'Synthetic cancellation failure'; END IF; RETURN NEW; END; $$;
CREATE TRIGGER test_fail_cancel BEFORE UPDATE ON venue_booking FOR EACH ROW EXECUTE FUNCTION pg_temp.fail_sibling_cancel();
SET LOCAL ROLE authenticated;
DO $$ BEGIN
 BEGIN
  PERFORM confirm_venue_booking('40000000-0000-0000-0000-000000000004');
  RAISE EXCEPTION 'Injected cancellation failure was ignored';
 EXCEPTION WHEN raise_exception THEN
  IF SQLERRM<>'Synthetic cancellation failure' THEN RAISE; END IF;
 END;
END; $$;
SELECT pg_temp.check_true((SELECT bool_and(status='requested') FROM venue_booking
 WHERE event_id='30000000-0000-0000-0000-000000000003'),'Failed cancellation must roll back all booking status changes');
SELECT confirm_venue_booking('40000000-0000-0000-0000-000000000006');
RESET ROLE;
SELECT set_config('request.jwt.claim.sub','',true);
INSERT INTO equipment(equipment_id,name,type,total_quantity) VALUES('10000000-0000-0000-0000-000000000001','Projector','Projector',1);
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
SELECT reservation_id AS proposal_a FROM propose_equipment_quantity('30000000-0000-0000-0000-000000000001',
 '10000000-0000-0000-0000-000000000001',1,'2026-11-20 09:00+08','2026-11-20 12:00+08') \gset
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
SELECT agree_equipment_proposal(:'proposal_a',1);
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
SELECT accept_equipment_request(:'proposal_a');
SELECT reservation_id AS proposal_b FROM propose_equipment_quantity('30000000-0000-0000-0000-000000000004',
 '10000000-0000-0000-0000-000000000001',1,'2026-11-20 12:29+08','2026-11-20 14:00+08') \gset
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
SELECT agree_equipment_proposal(:'proposal_b',1);
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
SELECT pg_temp.check_true(cs_equipment_request_available(:'proposal_b')=0,'29-minute cross-venue equipment transfer must fail');
RESET ROLE;
-- Existing accepted equipment must tolerate a new non-blocking alternative.
INSERT INTO venue_booking(booking_id,event_id,venue_id,requested_start,requested_end,status,setup_layout)
VALUES('40000000-0000-0000-0000-000000000007','30000000-0000-0000-0000-000000000001',
 '20000000-0000-0000-0000-000000000002','2026-11-22 09:00+08','2026-11-22 12:00+08','requested','Classroom');
SELECT pg_temp.check_true(cs_equipment_schedule_fits('10000000-0000-0000-0000-000000000001'),'Non-blocking alternative must not invalidate committed equipment');
-- Release the other event's selected booking before revising its period.
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000004',true);
UPDATE venue_booking SET status='cancelled' WHERE booking_id='40000000-0000-0000-0000-000000000006';
SELECT set_config('request.jwt.claim.sub','',true);
INSERT INTO venue_booking(booking_id,event_id,venue_id,requested_start,requested_end,status,setup_layout)
VALUES('40000000-0000-0000-0000-000000000008','30000000-0000-0000-0000-000000000004',
 '20000000-0000-0000-0000-000000000002','2026-11-20 12:30+08','2026-11-20 14:00+08','requested','Theatre');
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000004',true);
SELECT confirm_venue_booking('40000000-0000-0000-0000-000000000008');
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
SELECT propose_equipment_quantity('30000000-0000-0000-0000-000000000004',
 '10000000-0000-0000-0000-000000000001',1,'2026-11-20 12:30+08','2026-11-20 14:00+08',:'proposal_b',1);
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
SELECT agree_equipment_proposal(:'proposal_b',2);
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
SELECT pg_temp.check_true(cs_equipment_request_available(:'proposal_b')=1,'30-minute cross-venue equipment transfer must pass');
SELECT accept_equipment_request(:'proposal_b');
RESET ROLE;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000004',true);
SELECT b1_save_venue_buffers('20000000-0000-0000-0000-000000000002',20,20,1,
 '90000000-0000-0000-0000-000000000001');
SELECT b1_save_venue_buffers('20000000-0000-0000-0000-000000000002',20,20,1,
 '90000000-0000-0000-0000-000000000001');
SELECT pg_temp.check_true((SELECT buffer_config_revision=2 FROM venue WHERE venue_id='20000000-0000-0000-0000-000000000002'),'B1 save and receipt retry must preserve revision behavior');
SELECT pg_temp.check_true((SELECT bool_and(status='approved') FROM event),'Venue/equipment operations must not confirm events');
SELECT pg_temp.check_true(NOT has_function_privilege('anon','confirm_venue_booking(uuid)','EXECUTE'),'Anonymous confirmation execute must be denied');
ROLLBACK;
