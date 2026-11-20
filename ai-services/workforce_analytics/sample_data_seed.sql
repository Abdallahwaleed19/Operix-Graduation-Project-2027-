-- =============================================================================
-- Operix — Workforce Analytics Sample Data Seed
-- Target DB : operix_db (PostgreSQL 18)
-- Safety    : READ roles/permissions first; INSERT only into empty tables.
--             All in one transaction — ROLLBACK on any error.
--             No DELETE / TRUNCATE / ALTER / DROP statements used.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Capture existing role IDs (seeded by DDL, do NOT re-insert)
-- ---------------------------------------------------------------------------
DO $$ BEGIN
  IF (SELECT COUNT(*) FROM roles) = 0 THEN
    RAISE EXCEPTION 'roles table is empty — DDL seed was not run';
  END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 1. FACTORY
-- ---------------------------------------------------------------------------
INSERT INTO factories (id, name, slug, status, timezone, evidence_retention_days)
VALUES (
  'aaaaaaaa-0001-0001-0001-000000000001',
  'Operix Demo Factory',
  'operix-demo',
  'active',
  'Africa/Cairo',
  60
)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2. USERS  (password_hash is a bcrypt placeholder — never a real password)
-- ---------------------------------------------------------------------------
INSERT INTO users (id, email, password_hash, full_name, status, is_platform_admin, activated_at)
VALUES
  ('bbbbbbbb-0001-0001-0001-000000000001', 'abdallah.waleed@operix.demo',  '$2b$12$PLACEHOLDER_HASH_ABDALLAH',  'Abdallah Waleed',    'active', false, now() - INTERVAL '30 days'),
  ('bbbbbbbb-0002-0002-0002-000000000002', 'seif.sameh@operix.demo',       '$2b$12$PLACEHOLDER_HASH_SEIF',       'Seif Sameh',         'active', false, now() - INTERVAL '29 days'),
  ('bbbbbbbb-0003-0003-0003-000000000003', 'mohamed.shaheen@operix.demo',  '$2b$12$PLACEHOLDER_HASH_SHAHEEN',   'Mohamed Shaheen',    'active', false, now() - INTERVAL '28 days'),
  ('bbbbbbbb-0004-0004-0004-000000000004', 'toka.medhat@operix.demo',      '$2b$12$PLACEHOLDER_HASH_TOKA',      'Toka Medhat',        'active', false, now() - INTERVAL '28 days'),
  ('bbbbbbbb-0005-0005-0005-000000000005', 'ahmed.hassan@operix.demo',     '$2b$12$PLACEHOLDER_HASH_AHMED',     'Ahmed Hassan',       'active', false, now() - INTERVAL '25 days'),
  ('bbbbbbbb-0006-0006-0006-000000000006', 'mahmoud.ali@operix.demo',      '$2b$12$PLACEHOLDER_HASH_MAHMOUD',   'Mahmoud Ali',        'active', false, now() - INTERVAL '24 days'),
  ('bbbbbbbb-0007-0007-0007-000000000007', 'khaled.ibrahim@operix.demo',   '$2b$12$PLACEHOLDER_HASH_KHALED',   'Khaled Ibrahim',     'active', false, now() - INTERVAL '20 days'),
  ('bbbbbbbb-0008-0008-0008-000000000008', 'sara.youssef@operix.demo',     '$2b$12$PLACEHOLDER_HASH_SARA',      'Sara Youssef',       'disabled', false, now() - INTERVAL '30 days')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3. FACTORY_MEMBERSHIPS  (factory_id, user_id) → role
-- ---------------------------------------------------------------------------
INSERT INTO factory_memberships (factory_id, user_id, role_id, is_active)
SELECT
  'aaaaaaaa-0001-0001-0001-000000000001',
  u.uid,
  r.id,
  u.is_active
FROM (VALUES
  ('bbbbbbbb-0001-0001-0001-000000000001'::uuid, 'factory_admin',     true),
  ('bbbbbbbb-0002-0002-0002-000000000002'::uuid, 'factory_manager',   true),
  ('bbbbbbbb-0003-0003-0003-000000000003'::uuid, 'factory_manager',   true),
  ('bbbbbbbb-0004-0004-0004-000000000004'::uuid, 'safety_supervisor', true),
  ('bbbbbbbb-0005-0005-0005-000000000005'::uuid, 'safety_supervisor', true),
  ('bbbbbbbb-0006-0006-0006-000000000006'::uuid, 'safety_supervisor', true),
  ('bbbbbbbb-0007-0007-0007-000000000007'::uuid, 'safety_supervisor', true),
  ('bbbbbbbb-0008-0008-0008-000000000008'::uuid, 'safety_supervisor', false)
) AS u(uid, role_code, is_active)
JOIN roles r ON r.code = u.role_code
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. DEPARTMENTS
-- ---------------------------------------------------------------------------
INSERT INTO departments (id, factory_id, name)
VALUES
  ('cccccccc-0001-0001-0001-000000000001', 'aaaaaaaa-0001-0001-0001-000000000001', 'Welding Zone'),
  ('cccccccc-0002-0002-0002-000000000002', 'aaaaaaaa-0001-0001-0001-000000000001', 'Warehouse'),
  ('cccccccc-0003-0003-0003-000000000003', 'aaaaaaaa-0001-0001-0001-000000000001', 'Maintenance')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. CAMERAS
-- ---------------------------------------------------------------------------
INSERT INTO cameras (id, factory_id, department_id, name, camera_type, location_label, stream_url_ref, status, is_active)
VALUES
  ('dddddddd-0001-0001-0001-000000000001', 'aaaaaaaa-0001-0001-0001-000000000001', 'cccccccc-0001-0001-0001-000000000001', 'Welding-CAM-01', 'cctv', 'Welding Bay A',    'secret:welding-cam-01',   'available',   true),
  ('dddddddd-0002-0002-0002-000000000002', 'aaaaaaaa-0001-0001-0001-000000000001', 'cccccccc-0001-0001-0001-000000000001', 'Welding-CAM-02', 'cctv', 'Welding Bay B',    'secret:welding-cam-02',   'available',   true),
  ('dddddddd-0003-0003-0003-000000000003', 'aaaaaaaa-0001-0001-0001-000000000001', 'cccccccc-0002-0002-0002-000000000002', 'Warehouse-CAM-01','cctv','Warehouse Entry',  'secret:warehouse-cam-01', 'available',   true),
  ('dddddddd-0004-0004-0004-000000000004', 'aaaaaaaa-0001-0001-0001-000000000001', 'cccccccc-0003-0003-0003-000000000003', 'Maint-CAM-01',   'cctv', 'Maintenance Hall', 'secret:maint-cam-01',     'unavailable', false)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. MONITORING ZONES (3-point polygon min — using simple rectangles)
-- ---------------------------------------------------------------------------
INSERT INTO monitoring_zones (id, factory_id, camera_id, department_id, name, zone_type, polygon)
VALUES
  ('eeeeeeee-0001-0001-0001-000000000001',
   'aaaaaaaa-0001-0001-0001-000000000001',
   'dddddddd-0001-0001-0001-000000000001',
   'cccccccc-0001-0001-0001-000000000001',
   'Welding Restricted Zone',
   'restricted',
   '[[0.1,0.1],[0.5,0.1],[0.5,0.5],[0.1,0.5]]'::jsonb),
  ('eeeeeeee-0002-0002-0002-000000000002',
   'aaaaaaaa-0001-0001-0001-000000000001',
   'dddddddd-0003-0003-0003-000000000003',
   'cccccccc-0002-0002-0002-000000000002',
   'Warehouse PPE Zone',
   'ppe_required',
   '[[0.2,0.2],[0.8,0.2],[0.8,0.8],[0.2,0.8]]'::jsonb)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 7. SAFETY RULES
-- ---------------------------------------------------------------------------
INSERT INTO safety_rules (id, factory_id, name, event_type, severity, zone_id, min_confidence, notify)
VALUES
  ('ffffffff-0001-0001-0001-000000000001',
   'aaaaaaaa-0001-0001-0001-000000000001',
   'PPE Violation — Welding',
   'ppe_violation', 'high',
   'eeeeeeee-0001-0001-0001-000000000001',
   0.75, true),
  ('ffffffff-0002-0002-0002-000000000002',
   'aaaaaaaa-0001-0001-0001-000000000001',
   'Restricted Zone Intrusion',
   'restricted_zone_intrusion', 'critical',
   'eeeeeeee-0001-0001-0001-000000000001',
   0.80, true),
  ('ffffffff-0003-0003-0003-000000000003',
   'aaaaaaaa-0001-0001-0001-000000000001',
   'Potential Fatigue Detection',
   'potential_fatigue', 'medium',
   NULL, 0.70, true)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 8. INCIDENTS (15 incidents over last 30 days with realistic states)
-- ---------------------------------------------------------------------------
INSERT INTO incidents (id, factory_id, incident_type, severity, state, opened_at, last_event_at,
                        reviewed_by, reviewed_at, resolved_by, resolved_at, resolution_note)
VALUES
  -- Resolved incidents (reviewer & resolver)
  ('11111111-0001-0001-0001-000000000001', 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',              'high',     'resolved',      now()-'28 days'::interval, now()-'28 days'::interval, 'bbbbbbbb-0004-0004-0004-000000000004', now()-'27 days 23h'::interval, 'bbbbbbbb-0002-0002-0002-000000000002', now()-'27 days 20h'::interval, 'Worker warned and re-equipped.'),
  ('11111111-0002-0002-0002-000000000002', 'aaaaaaaa-0001-0001-0001-000000000001', 'restricted_zone_intrusion',  'critical',  'resolved',      now()-'26 days'::interval, now()-'26 days'::interval, 'bbbbbbbb-0005-0005-0005-000000000005', now()-'25 days 22h'::interval, 'bbbbbbbb-0003-0003-0003-000000000003', now()-'25 days 18h'::interval, 'Zone access revoked.'),
  ('11111111-0003-0003-0003-000000000003', 'aaaaaaaa-0001-0001-0001-000000000001', 'potential_fatigue',          'medium',    'resolved',      now()-'24 days'::interval, now()-'24 days'::interval, 'bbbbbbbb-0004-0004-0004-000000000004', now()-'23 days 20h'::interval, 'bbbbbbbb-0002-0002-0002-000000000002', now()-'23 days 15h'::interval, 'Worker given break and monitored.'),
  ('11111111-0004-0004-0004-000000000004', 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',              'high',     'resolved',      now()-'22 days'::interval, now()-'22 days'::interval, 'bbbbbbbb-0006-0006-0006-000000000006', now()-'21 days 23h'::interval, 'bbbbbbbb-0003-0003-0003-000000000003', now()-'21 days 20h'::interval, 'PPE compliance retrained.'),
  ('11111111-0005-0005-0005-000000000005', 'aaaaaaaa-0001-0001-0001-000000000001', 'fall',                       'critical',  'resolved',      now()-'20 days'::interval, now()-'20 days'::interval, 'bbbbbbbb-0005-0005-0005-000000000005', now()-'19 days 20h'::interval, 'bbbbbbbb-0002-0002-0002-000000000002', now()-'19 days 14h'::interval, 'First aid administered; area secured.'),
  ('11111111-0006-0006-0006-000000000006', 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',              'medium',    'resolved',      now()-'18 days'::interval, now()-'18 days'::interval, 'bbbbbbbb-0007-0007-0007-000000000007', now()-'17 days 22h'::interval, 'bbbbbbbb-0003-0003-0003-000000000003', now()-'17 days 19h'::interval, 'Issued written warning.'),
  ('11111111-0007-0007-0007-000000000007', 'aaaaaaaa-0001-0001-0001-000000000001', 'potential_fatigue',          'low',       'resolved',      now()-'16 days'::interval, now()-'16 days'::interval, 'bbbbbbbb-0004-0004-0004-000000000004', now()-'15 days 20h'::interval, 'bbbbbbbb-0002-0002-0002-000000000002', now()-'15 days 16h'::interval, 'Scheduled additional rest breaks.'),
  -- Under review incidents
  ('11111111-0008-0008-0008-000000000008', 'aaaaaaaa-0001-0001-0001-000000000001', 'restricted_zone_intrusion',  'high',     'under_review',  now()-'10 days'::interval, now()-'10 days'::interval, 'bbbbbbbb-0006-0006-0006-000000000006', now()-'9 days 22h'::interval,  NULL, NULL, NULL),
  ('11111111-0009-0009-0009-000000000009', 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',              'high',     'under_review',  now()-'8 days'::interval,  now()-'8 days'::interval,  'bbbbbbbb-0005-0005-0005-000000000005', now()-'7 days 22h'::interval,  NULL, NULL, NULL),
  ('11111111-000a-000a-000a-00000000000a', 'aaaaaaaa-0001-0001-0001-000000000001', 'potential_fatigue',          'medium',    'under_review',  now()-'6 days'::interval,  now()-'6 days'::interval,  'bbbbbbbb-0007-0007-0007-000000000007', now()-'5 days 20h'::interval,  NULL, NULL, NULL),
  -- Alert pending / recorded
  ('11111111-000b-000b-000b-00000000000b', 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',              'critical',  'alert_pending', now()-'4 days'::interval,  now()-'4 days'::interval,  NULL, NULL, NULL, NULL, NULL),
  ('11111111-000c-000c-000c-00000000000c', 'aaaaaaaa-0001-0001-0001-000000000001', 'fall',                       'critical',  'recorded',      now()-'3 days'::interval,  now()-'3 days'::interval,  NULL, NULL, NULL, NULL, NULL),
  -- Classified / detected
  ('11111111-000d-000d-000d-00000000000d', 'aaaaaaaa-0001-0001-0001-000000000001', 'restricted_zone_intrusion',  'high',     'classified',    now()-'2 days'::interval,  now()-'2 days'::interval,  NULL, NULL, NULL, NULL, NULL),
  ('11111111-000e-000e-000e-00000000000e', 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',              'medium',    'detected',      now()-'1 day'::interval,   now()-'1 day'::interval,   NULL, NULL, NULL, NULL, NULL),
  ('11111111-000f-000f-000f-00000000000f', 'aaaaaaaa-0001-0001-0001-000000000001', 'potential_fatigue',          'low',       'detected',      now()-'12 hours'::interval, now()-'12 hours'::interval, NULL, NULL, NULL, NULL, NULL)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 9. EVENTS (1 per incident — camera source, satisfies CHECK num_nonnulls=1)
-- ---------------------------------------------------------------------------
INSERT INTO events (id, factory_id, event_type, camera_id, zone_id, rule_id, incident_id,
                    detected_at, confidence, track_ref, details)
VALUES
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',             'dddddddd-0001-0001-0001-000000000001', 'eeeeeeee-0001-0001-0001-000000000001', 'ffffffff-0001-0001-0001-000000000001', '11111111-0001-0001-0001-000000000001', now()-'28 days'::interval,  0.92, 101, '{"missing_items":["helmet"]}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'restricted_zone_intrusion', 'dddddddd-0001-0001-0001-000000000001', 'eeeeeeee-0001-0001-0001-000000000001', 'ffffffff-0002-0002-0002-000000000002', '11111111-0002-0002-0002-000000000002', now()-'26 days'::interval,  0.88, 102, '{"zone":"Welding Restricted"}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'potential_fatigue',         'dddddddd-0002-0002-0002-000000000002', NULL,                                   'ffffffff-0003-0003-0003-000000000003', '11111111-0003-0003-0003-000000000003', now()-'24 days'::interval,  0.79, 103, '{"fatigue_score":0.82}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',             'dddddddd-0001-0001-0001-000000000001', 'eeeeeeee-0001-0001-0001-000000000001', 'ffffffff-0001-0001-0001-000000000001', '11111111-0004-0004-0004-000000000004', now()-'22 days'::interval,  0.95, 104, '{"missing_items":["gloves","helmet"]}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'fall',                      'dddddddd-0002-0002-0002-000000000002', NULL,                                   NULL,                                   '11111111-0005-0005-0005-000000000005', now()-'20 days'::interval,  0.97, 105, '{"location":"Welding Bay B"}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',             'dddddddd-0003-0003-0003-000000000003', 'eeeeeeee-0002-0002-0002-000000000002', 'ffffffff-0001-0001-0001-000000000001', '11111111-0006-0006-0006-000000000006', now()-'18 days'::interval,  0.83, 106, '{"missing_items":["vest"]}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'potential_fatigue',         'dddddddd-0001-0001-0001-000000000001', NULL,                                   'ffffffff-0003-0003-0003-000000000003', '11111111-0007-0007-0007-000000000007', now()-'16 days'::interval,  0.72, 107, '{"fatigue_score":0.68}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'restricted_zone_intrusion', 'dddddddd-0001-0001-0001-000000000001', 'eeeeeeee-0001-0001-0001-000000000001', 'ffffffff-0002-0002-0002-000000000002', '11111111-0008-0008-0008-000000000008', now()-'10 days'::interval,  0.91, 108, '{"zone":"Welding Restricted"}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',             'dddddddd-0001-0001-0001-000000000001', 'eeeeeeee-0001-0001-0001-000000000001', 'ffffffff-0001-0001-0001-000000000001', '11111111-0009-0009-0009-000000000009', now()-'8 days'::interval,   0.87, 109, '{"missing_items":["helmet"]}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'potential_fatigue',         'dddddddd-0002-0002-0002-000000000002', NULL,                                   'ffffffff-0003-0003-0003-000000000003', '11111111-000a-000a-000a-00000000000a', now()-'6 days'::interval,   0.74, 110, '{"fatigue_score":0.77}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',             'dddddddd-0001-0001-0001-000000000001', 'eeeeeeee-0001-0001-0001-000000000001', 'ffffffff-0001-0001-0001-000000000001', '11111111-000b-000b-000b-00000000000b', now()-'4 days'::interval,   0.96, 111, '{"missing_items":["helmet","gloves","vest"]}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'fall',                      'dddddddd-0003-0003-0003-000000000003', NULL,                                   NULL,                                   '11111111-000c-000c-000c-00000000000c', now()-'3 days'::interval,   0.98, 112, '{"location":"Warehouse Entry"}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'restricted_zone_intrusion', 'dddddddd-0001-0001-0001-000000000001', 'eeeeeeee-0001-0001-0001-000000000001', 'ffffffff-0002-0002-0002-000000000002', '11111111-000d-000d-000d-00000000000d', now()-'2 days'::interval,   0.85, 113, '{"zone":"Welding Restricted"}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'ppe_violation',             'dddddddd-0002-0002-0002-000000000002', NULL,                                   'ffffffff-0001-0001-0001-000000000001', '11111111-000e-000e-000e-00000000000e', now()-'1 day'::interval,    0.78, 114, '{"missing_items":["gloves"]}'::jsonb),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'potential_fatigue',         'dddddddd-0001-0001-0001-000000000001', NULL,                                   'ffffffff-0003-0003-0003-000000000003', '11111111-000f-000f-000f-00000000000f', now()-'12 hours'::interval,  0.71, 115, '{"fatigue_score":0.73}'::jsonb)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 10. UNOBSERVED GAPS (camera downtime — for coverage analytics)
-- ---------------------------------------------------------------------------
INSERT INTO unobserved_gaps (id, factory_id, camera_id, started_at, ended_at, reason)
VALUES
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'dddddddd-0001-0001-0001-000000000001', now()-'15 days 6h'::interval,  now()-'15 days 4h'::interval,  'stream_lost'),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'dddddddd-0002-0002-0002-000000000002', now()-'10 days 8h'::interval,  now()-'10 days 7h'::interval,  'poor_quality'),
  (gen_random_uuid(), 'aaaaaaaa-0001-0001-0001-000000000001', 'dddddddd-0003-0003-0003-000000000003', now()-'5 days 10h'::interval,  now()-'5 days 9h'::interval,   'camera_blocked')
ON CONFLICT DO NOTHING;

COMMIT;

-- Verification queries
SELECT 'factories'          AS tbl, COUNT(*) FROM factories
UNION ALL SELECT 'users',              COUNT(*) FROM users
UNION ALL SELECT 'factory_memberships',COUNT(*) FROM factory_memberships
UNION ALL SELECT 'departments',        COUNT(*) FROM departments
UNION ALL SELECT 'cameras',            COUNT(*) FROM cameras
UNION ALL SELECT 'monitoring_zones',   COUNT(*) FROM monitoring_zones
UNION ALL SELECT 'safety_rules',       COUNT(*) FROM safety_rules
UNION ALL SELECT 'incidents',          COUNT(*) FROM incidents
UNION ALL SELECT 'events',             COUNT(*) FROM events
UNION ALL SELECT 'unobserved_gaps',    COUNT(*) FROM unobserved_gaps;
