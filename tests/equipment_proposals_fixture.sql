-- Synthetic local-only PostgreSQL fixture. Never run this file in Supabase.
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN;
CREATE SCHEMA auth;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
GRANT USAGE ON SCHEMA auth TO authenticated,anon;
GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated,anon;
CREATE TABLE public.profile(user_id uuid PRIMARY KEY,name text,active boolean DEFAULT true);
CREATE TABLE public.user_role(user_id uuid REFERENCES profile,role text,PRIMARY KEY(user_id,role));
CREATE TABLE public.event(event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),organiser_id uuid REFERENCES profile,
 coordinator_id uuid REFERENCES profile,name text,description text,technical_requirements text,venue_requirements text,
 technical_support_required boolean,start_datetime timestamptz,end_datetime timestamptz,
 preferred_start_datetime timestamptz,preferred_end_datetime timestamptz,created_at timestamptz DEFAULT now(),
 status text CHECK(status IN ('draft','requested','changes_requested','planning','confirmed','completed','cancelled','withdrawn','rejected')));
CREATE TABLE public.venue(venue_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),name text,location text,active boolean DEFAULT true);
CREATE TABLE public.venue_booking(booking_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),event_id uuid REFERENCES event,
 venue_id uuid REFERENCES venue,requested_start timestamptz,requested_end timestamptz,
 status text CHECK(status IN ('requested','tentative','confirmed','rejected','cancelled')));
CREATE TABLE public.venue_block(venue_block_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),venue_id uuid REFERENCES venue,
 start_datetime timestamptz,end_datetime timestamptz,status text CHECK(status IN ('active','cancelled')));
CREATE TABLE public.equipment(equipment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),name text,type text,total_quantity integer,active boolean DEFAULT true);
CREATE TABLE public.equipment_reservation(reservation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),event_id uuid REFERENCES event,
 equipment_id uuid REFERENCES equipment,quantity_requested integer,start_datetime timestamptz,end_datetime timestamptz,
 technical_requirements text,status text CHECK(status IN ('requested','reserved','rejected','cancelled')),
 requested_by uuid REFERENCES profile,requested_at timestamptz,decided_by uuid REFERENCES profile,decided_at timestamptz,decision_reason text);
CREATE TABLE public.equipment_unavailability(equipment_unavailability_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 equipment_id uuid REFERENCES equipment,quantity_unavailable integer,start_datetime timestamptz,end_datetime timestamptz,
 created_by uuid REFERENCES profile,status text CHECK(status IN ('active','cancelled')));
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
ALTER TABLE user_role ENABLE ROW LEVEL SECURITY;
ALTER TABLE profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE event ENABLE ROW LEVEL SECURITY;
ALTER TABLE venue ENABLE ROW LEVEL SECURITY;
ALTER TABLE venue_booking ENABLE ROW LEVEL SECURITY;
ALTER TABLE venue_block ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment_reservation ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment_unavailability ENABLE ROW LEVEL SECURITY;
CREATE POLICY own_role ON user_role FOR SELECT TO authenticated USING(user_id=auth.uid());
CREATE POLICY own_profile ON profile FOR SELECT TO authenticated USING(user_id=auth.uid());
CREATE POLICY own_event ON event FOR SELECT TO authenticated USING(organiser_id=auth.uid());
CREATE POLICY own_event_edit ON event FOR UPDATE TO authenticated USING(organiser_id=auth.uid()) WITH CHECK(organiser_id=auth.uid());
CREATE POLICY coordinator_event ON event TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='event_coordinator'));
CREATE FUNCTION public.cs_technical_support_can_view_event(p_event_id uuid) RETURNS boolean LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
 SELECT EXISTS(SELECT 1 FROM public.user_role WHERE user_id=auth.uid() AND role='technical_support') AND EXISTS(SELECT 1 FROM public.equipment_reservation WHERE event_id=p_event_id) $$;
CREATE POLICY technical_event ON event FOR SELECT TO authenticated USING(public.cs_technical_support_can_view_event(event_id));
CREATE POLICY technical_equipment ON equipment FOR SELECT TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='technical_support'));
CREATE POLICY technical_requests ON equipment_reservation FOR SELECT TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='technical_support'));
CREATE POLICY technical_insert ON equipment_reservation FOR INSERT TO authenticated WITH CHECK(requested_by=auth.uid() AND EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='technical_support'));
CREATE POLICY technical_update ON equipment_reservation FOR UPDATE TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='technical_support'));
CREATE POLICY coordinator_requests ON equipment_reservation FOR SELECT TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='event_coordinator'));
CREATE POLICY technical_unavailability ON equipment_unavailability TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='technical_support'));
CREATE POLICY supported_bookings ON venue_booking FOR SELECT TO authenticated USING(EXISTS(SELECT 1 FROM equipment_reservation r WHERE r.event_id=venue_booking.event_id));
CREATE POLICY staff_bookings ON venue_booking TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='venue_staff'));
CREATE POLICY supported_venues ON venue FOR SELECT TO authenticated USING(EXISTS(SELECT 1 FROM venue_booking b WHERE b.venue_id=venue.venue_id));
CREATE POLICY staff_venues ON venue TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='venue_staff'));
CREATE POLICY staff_blocks ON venue_block TO authenticated USING(EXISTS(SELECT 1 FROM user_role WHERE user_id=auth.uid() AND role='venue_staff'));
INSERT INTO profile(user_id,name) VALUES
 ('00000000-0000-0000-0000-000000000001','Organiser A'),('00000000-0000-0000-0000-000000000002','Technical Support'),
 ('00000000-0000-0000-0000-000000000003','Other Organiser'),('00000000-0000-0000-0000-000000000004','Venue Staff');
INSERT INTO user_role VALUES
 ('00000000-0000-0000-0000-000000000001','event_organiser'),('00000000-0000-0000-0000-000000000002','technical_support'),
 ('00000000-0000-0000-0000-000000000003','event_organiser'),('00000000-0000-0000-0000-000000000004','venue_staff');
-- Every test runs its own rollback, reusing deterministic synthetic IDs.
CREATE FUNCTION public.test_equipment_setup(p_total integer DEFAULT 5,p_b_start text DEFAULT '12:30',p_same_venue boolean DEFAULT false)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO equipment(equipment_id,name,type,total_quantity) VALUES('10000000-0000-0000-0000-000000000001','Projector','Projector',p_total);
 INSERT INTO venue(venue_id,name,location) VALUES('20000000-0000-0000-0000-000000000001','Room A','Same building'),('20000000-0000-0000-0000-000000000002','Room B','Same building');
 INSERT INTO event(event_id,organiser_id,name,status,technical_support_required,technical_requirements,preferred_start_datetime,preferred_end_datetime) VALUES
 ('30000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','Organiser Event A','planning',true,'Five projectors please','2026-11-20 09:00+08','2026-11-20 12:00+08'),
 ('30000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','Organiser Event B','planning',true,'One projector please',('2026-11-20 '||p_b_start||'+08')::timestamptz,'2026-11-20 14:00+08');
 INSERT INTO venue_booking(booking_id,event_id,venue_id,requested_start,requested_end,status) VALUES
 ('40000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','2026-11-20 09:00+08','2026-11-20 12:00+08','confirmed'),
 ('40000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000002',CASE WHEN p_same_venue THEN '20000000-0000-0000-0000-000000000001' ELSE '20000000-0000-0000-0000-000000000002' END::uuid,('2026-11-20 '||p_b_start||'+08')::timestamptz,'2026-11-20 14:00+08','confirmed');
END; $$;
