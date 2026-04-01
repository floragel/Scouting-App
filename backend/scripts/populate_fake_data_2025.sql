-- ==========================================
-- 2025 FESTIVAL DE ROBOTIQUE REGIONAL FAKE DATA
-- ==========================================
-- Purpose: Testing Pick List, Drive Team Briefing, and Stat Dashboards.
-- Target Event: Festival de Robotique Regional 2025 (Montreal)
-- Reversibility: Use the DELETE command at the end.

BEGIN;

-- 1. INSERT THE EVENT
-- Key: '2025qcmo'
INSERT INTO event (tba_key, name, location, date, status)
VALUES ('2025qcmo', 'Festival de Robotique Regional 2025', 'Montreal, QC', '2025-03-27', 'ongoing')
ON CONFLICT (tba_key) DO UPDATE SET status = 'ongoing';

-- 2. INSERT TEAMS (If they don't exist)
INSERT INTO team (tba_key, team_number, team_name, nickname) VALUES
('frc6622', 6622, 'StanRobotix', 'StanRobotix'),
('frc254', 254, 'The Cheesy Poofs', 'Cheesy Poofs'),
('frc1678', 1678, 'Citrus Circuits', 'Citrus Circuits'),
('frc3550', 3550, 'Le Taz', 'Le Taz'),
('frc3990', 3990, 'Tech for Kids', 'Tech for Kids')
ON CONFLICT (tba_key) DO NOTHING;

-- 3. LINK TEAMS TO EVENT
INSERT INTO event_team (event_id, team_id)
SELECT e.id, t.id FROM event e, team t
WHERE e.tba_key = '2025qcmo' AND t.tba_key IN ('frc6622', 'frc254', 'frc1678', 'frc3550', 'frc3990')
ON CONFLICT DO NOTHING;

-- 4. PIT SCOUT DATA (Logical Specs for 2025)
INSERT INTO pit_scout_data (team_id, event_id, drivetrain_type, weight, motor_type, motor_count, dimensions_l, dimensions_w, auto_leave, auto_score_fuel, climb_level, intake_type, notes)
SELECT t.id, e.id, 
       CASE WHEN t.team_number IN (254, 1678, 6622) THEN 'Swerve' ELSE 'Tank' END,
       120.0, 
       'Kraken X60', 4, 30.0, 30.0, 
       TRUE, TRUE, 'L3', 'Both', 
       'Excellent robot condition. High build quality.'
FROM team t, event e
WHERE e.tba_key = '2025qcmo' AND t.tba_key IN ('frc6622', 'frc254', 'frc1678', 'frc3550', 'frc3990')
ON CONFLICT (team_id, event_id) DO NOTHING;

-- 5. MATCH SCOUT DATA (Match 1)
INSERT INTO match_scout_data (team_id, event_id, match_number, auto_balls_scored, teleop_balls_shot, teleop_shooter_accuracy, endgame_climb, notes)
SELECT t.id, e.id, 1, 
       CASE WHEN t.team_number IN (254, 1678) THEN 6 ELSE 3 END,
       CASE WHEN t.team_number IN (254, 1678) THEN 30 ELSE 15 END,
       4, 'L3', 'Very consistent shooter.'
FROM team t, event e
WHERE e.tba_key = '2025qcmo' AND t.tba_key IN ('frc6622', 'frc254', 'frc1678', 'frc3550', 'frc3990')
ON CONFLICT (team_id, event_id, match_number) DO NOTHING;

-- 6. MATCH SCOUT DATA (Match 15)
INSERT INTO match_scout_data (team_id, event_id, match_number, auto_balls_scored, teleop_balls_shot, teleop_shooter_accuracy, endgame_climb, notes)
SELECT t.id, e.id, 15, 
       CASE WHEN t.team_number IN (254, 1678) THEN 7 ELSE 4 END,
       CASE WHEN t.team_number IN (254, 1678) THEN 35 ELSE 18 END,
       5, 'L3', 'Dominant match performance.'
FROM team t, event e
WHERE e.tba_key = '2025qcmo' AND t.tba_key IN ('frc6622', 'frc254', 'frc1678', 'frc3550', 'frc3990')
ON CONFLICT (team_id, event_id, match_number) DO NOTHING;

-- 7. MATCH SCOUT DATA (Match 30) - Random failure for 3550 for testing
INSERT INTO match_scout_data (team_id, event_id, match_number, auto_balls_scored, teleop_balls_shot, teleop_shooter_accuracy, endgame_climb, notes)
SELECT t.id, e.id, 30, 
       0, 5, 2, 'None', 'Broke drivetrain mid-match.'
FROM team t, event e
WHERE e.tba_key = '2025qcmo' AND t.tba_key = 'frc3550'
ON CONFLICT (team_id, event_id, match_number) DO NOTHING;

COMMIT;

-- ==========================================
-- REVERSAL (CLEANUP)
-- ==========================================
-- To remove all fake data and the event, run these commands:
-- 1. DELETE FROM match_scout_data WHERE event_id IN (SELECT id FROM event WHERE tba_key = '2025qcmo');
-- 2. DELETE FROM pit_scout_data WHERE event_id IN (SELECT id FROM event WHERE tba_key = '2025qcmo');
-- 3. DELETE FROM event_team WHERE event_id IN (SELECT id FROM event WHERE tba_key = '2025qcmo');
-- 4. DELETE FROM event WHERE tba_key = '2025qcmo';
