-- ==========================================
-- 2026 FESTIVAL DE ROBOTIQUE REGIONAL FAKE DATA
-- ==========================================
-- This script adds data for the 2026 season so it shows up on your default dashboard.
-- Reversibility: Use the DELETE command at the end.

BEGIN;

-- 1. INSERT THE EVENT FOR 2026
-- Key: '2026qcmo' (Montreal)
INSERT INTO event (tba_key, name, location, date, status)
VALUES ('2026qcmo', 'Festival de Robotique Regional 2026', 'Montreal, QC', '2026-03-26', 'ongoing')
ON CONFLICT (tba_key) DO UPDATE SET status = 'ongoing';

-- 2. INSERT TEAMS (If they don't exist)
INSERT INTO team (tba_key, team_number, team_name, nickname) VALUES
('frc6622', 6622, 'StanRobotix', 'StanRobotix'),
('frc254', 254, 'The Cheesy Poofs', 'Cheesy Poofs'),
('frc1678', 1678, 'Citrus Circuits', 'Citrus Circuits'),
('frc3550', 3550, 'Le Taz', 'Le Taz'),
('frc3990', 3990, 'Tech for Kids', 'Tech for Kids')
ON CONFLICT (tba_key) DO NOTHING;

-- 3. LINK TEAMS TO 2026 EVENT
INSERT INTO event_team (event_id, team_id)
SELECT e.id, t.id FROM event e, team t
WHERE e.tba_key = '2026qcmo' AND t.tba_key IN ('frc6622', 'frc254', 'frc1678', 'frc3550', 'frc3990')
ON CONFLICT DO NOTHING;

-- 4. PIT SCOUT DATA (Linked to an existing user if available)
INSERT INTO pit_scout_data (team_id, event_id, scouter_id, drivetrain_type, weight, motor_type, motor_count, dimensions_l, dimensions_w, auto_leave, auto_score_fuel, max_fuel_capacity, climb_level, intake_type, notes)
SELECT t.id, e.id, (SELECT id FROM "user" LIMIT 1), 
       CASE WHEN t.team_number IN (254, 1678, 6622) THEN 'Swerve' ELSE 'Tank' END,
       118.5 + (RANDOM() * 8.0), 
       'Kraken X60', 4, 30.0, 30.0, 
       TRUE, TRUE, 50, 'L3', 'Both', 
       'Excellent robot construction. Very robust components.'
FROM team t, event e
WHERE e.tba_key = '2026qcmo' AND t.tba_key IN ('frc6622', 'frc254', 'frc1678', 'frc3550', 'frc3990')
ON CONFLICT (team_id, event_id) DO NOTHING;

-- 5. MATCH SCOUT DATA (Linked to an existing user if available)
-- Match 1
INSERT INTO match_scout_data (team_id, event_id, match_number, scouter_id, auto_balls_scored, teleop_balls_shot, teleop_shooter_accuracy, teleop_intake_speed, endgame_climb, notes)
SELECT t.id, e.id, 1, (SELECT id FROM "user" LIMIT 1), 
       CASE WHEN t.team_number IN (254, 1678) THEN 6 ELSE 3 END,
       CASE WHEN t.team_number IN (254, 1678) THEN 32 ELSE 15 END,
       5, 4, 'L3', 'Fast and precise.'
FROM team t, event e
WHERE e.tba_key = '2026qcmo' AND t.tba_key IN ('frc6622', 'frc254', 'frc1678', 'frc3550', 'frc3990')
ON CONFLICT (team_id, event_id, match_number) DO NOTHING;

-- Match 10
INSERT INTO match_scout_data (team_id, event_id, match_number, scouter_id, auto_balls_scored, teleop_balls_shot, teleop_shooter_accuracy, teleop_intake_speed, endgame_climb, notes)
SELECT t.id, e.id, 10, (SELECT id FROM "user" LIMIT 1), 
       CASE WHEN t.team_number IN (254, 1678) THEN 8 ELSE 4 END,
       CASE WHEN t.team_number IN (254, 1678) THEN 38 ELSE 18 END,
       5, 5, 'L3', 'MVP performance.'
FROM team t, event e
WHERE e.tba_key = '2026qcmo' AND t.tba_key IN ('frc6622', 'frc254', 'frc1678', 'frc3550', 'frc3990')
ON CONFLICT (team_id, event_id, match_number) DO NOTHING;

COMMIT;

-- ==========================================
-- REVERSAL (CLEANUP)
-- ==========================================
-- 1. DELETE FROM match_scout_data WHERE event_id IN (SELECT id FROM event WHERE tba_key = '2026qcmo');
-- 2. DELETE FROM pit_scout_data WHERE event_id IN (SELECT id FROM event WHERE tba_key = '2026qcmo');
-- 3. DELETE FROM event_team WHERE event_id IN (SELECT id FROM event WHERE tba_key = '2026qcmo');
-- 4. DELETE FROM event WHERE tba_key = '2026qcmo';
