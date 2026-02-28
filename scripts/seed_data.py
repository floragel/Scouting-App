"""
Seed script: Populate the database with realistic random data for all teams
associated with the Festival de Robotique Régional (event key: 2024qcmo).

This creates:
  - Pit scouting data for every team
  - 4-8 match scouting entries per team (simulates a regional schedule)

Usage:
    cd backend && python seed_data.py
"""

import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import Team, Event, PitScoutData, MatchScoutData

# ── Configuration ───────────────────────────────────────────────────
EVENT_KEY = '2024qcmo'  # Festival de Robotique Régional
MATCHES_PER_TEAM = (4, 8)  # Random range of matches per team

DRIVETRAINS = ['Tank', 'Mecanum', 'Swerve', 'West Coast', 'H-Drive']
MOTOR_TYPES = ['NEO', 'Falcon 500', 'CIM', 'NEO 550', 'Kraken X60']
CLIMB_LEVELS = ['None', 'L1', 'L2', 'L3']
SCORING_PREFS = ['Low', 'High', 'Both']
INTAKE_TYPES = ['Ground', 'Chute', 'Both']
AUTO_CLIMB_OPTS = ['None', 'L1']

# Team archetypes for realistic variation
ARCHETYPES = {
    'elite':    {'weight': (0.15,), 'auto_scored': (3, 6), 'teleop_shot': (8, 15), 'intake': (4, 5), 'accuracy': (4, 5), 'climb_pct': 0.90, 'l3_pct': 0.70},
    'strong':   {'weight': (0.30,), 'auto_scored': (2, 4), 'teleop_shot': (5, 10), 'intake': (3, 5), 'accuracy': (3, 5), 'climb_pct': 0.75, 'l3_pct': 0.40},
    'average':  {'weight': (0.35,), 'auto_scored': (1, 3), 'teleop_shot': (3, 7),  'intake': (2, 4), 'accuracy': (2, 4), 'climb_pct': 0.50, 'l3_pct': 0.20},
    'rookie':   {'weight': (0.20,), 'auto_scored': (0, 2), 'teleop_shot': (1, 4),  'intake': (1, 3), 'accuracy': (1, 3), 'climb_pct': 0.25, 'l3_pct': 0.05},
}


def pick_archetype():
    """Weighted random archetype selection."""
    names = list(ARCHETYPES.keys())
    weights = [ARCHETYPES[n]['weight'][0] for n in names]
    return random.choices(names, weights=weights, k=1)[0]


def seed():
    with app.app_context():
        event = Event.query.filter_by(tba_key=EVENT_KEY).first()
        if not event:
            print(f"❌ Event with key '{EVENT_KEY}' not found in the database.")
            return

        teams = Team.query.all()
        if not teams:
            print("❌ No teams found in the database.")
            return

        # Link all teams to this event if not already linked
        for t in teams:
            if event not in t.events.all():
                t.events.append(event)
        db.session.commit()
        print(f"✅ Linked {len(teams)} teams to '{event.name}' (id={event.id})")

        # ── Clear existing seed data for this event ─────────
        deleted_pit = PitScoutData.query.filter_by(event_id=event.id).delete()
        deleted_match = MatchScoutData.query.filter_by(event_id=event.id).delete()
        db.session.commit()
        print(f"🗑️  Cleared {deleted_pit} old pit + {deleted_match} old match entries for this event")

        # ── Generate Pit + Match data ───────────────────────
        pit_count = 0
        match_count = 0

        for team in teams:
            archetype = pick_archetype()
            arch = ARCHETYPES[archetype]

            # ── PIT SCOUTING DATA ──
            drivetrain = random.choice(DRIVETRAINS)
            # Elite teams more likely to have Swerve
            if archetype == 'elite' and random.random() < 0.6:
                drivetrain = 'Swerve'

            weight = round(random.uniform(85, 125), 1)
            motor_type = random.choice(MOTOR_TYPES)
            motor_count = random.choice([4, 6, 8])
            dim_l = round(random.uniform(26, 33), 1)
            dim_w = round(random.uniform(26, 33), 1)

            max_climb = random.choices(
                CLIMB_LEVELS,
                weights=[0.05, 0.15, 0.30, 0.50] if archetype in ('elite', 'strong')
                else [0.20, 0.30, 0.30, 0.20],
                k=1
            )[0]

            pit = PitScoutData(
                team_id=team.id,
                event_id=event.id,
                drivetrain_type=drivetrain,
                weight=weight,
                motor_type=motor_type,
                motor_count=motor_count,
                dimensions_l=dim_l,
                dimensions_w=dim_w,
                auto_leave=random.random() < (0.95 if archetype in ('elite', 'strong') else 0.60),
                auto_score_fuel=random.random() < (0.85 if archetype in ('elite', 'strong') else 0.40),
                auto_collect_fuel=random.random() < 0.50,
                auto_climb_l1=random.random() < (0.70 if archetype == 'elite' else 0.20),
                max_fuel_capacity=random.randint(20, 80),
                climb_level=max_climb,
                scoring_preference=random.choice(SCORING_PREFS),
                intake_type=random.choice(INTAKE_TYPES),
                fits_under_trench=random.random() < 0.40,
                target_tower_level=max_climb,
                fuel_capacity=random.randint(10, 50),
                notes=f"[SEED] {archetype.capitalize()} tier robot. {drivetrain} drive, {motor_type} motors."
            )
            db.session.add(pit)
            pit_count += 1

            # ── MATCH SCOUTING DATA ──
            num_matches = random.randint(*MATCHES_PER_TEAM)
            for match_num in range(1, num_matches + 1):
                auto_scored = random.randint(*arch['auto_scored'])
                auto_shot = auto_scored + random.randint(0, 2)
                teleop_shot = random.randint(*arch['teleop_shot'])
                intake_speed = random.randint(*arch['intake'])
                accuracy = random.randint(*arch['accuracy'])

                # Determine climb result for this match
                did_climb = random.random() < arch['climb_pct']
                if did_climb:
                    got_l3 = random.random() < arch['l3_pct']
                    if got_l3:
                        climb = 'L3'
                    else:
                        climb = random.choice(['L1', 'L2'])
                else:
                    climb = 'None'

                match_entry = MatchScoutData(
                    team_id=team.id,
                    event_id=event.id,
                    match_number=match_num,
                    auto_start_balls=random.randint(0, 3),
                    auto_balls_shot=auto_shot,
                    auto_balls_scored=auto_scored,
                    auto_climb=random.choice(AUTO_CLIMB_OPTS),
                    teleop_intake_speed=intake_speed,
                    teleop_shooter_accuracy=accuracy,
                    teleop_balls_shot=teleop_shot,
                    passes_bump=random.random() < 0.60,
                    passes_trench=random.random() < 0.35,
                    endgame_climb=climb,
                    notes=f"[SEED] Match {match_num} - {archetype} class performance"
                )
                db.session.add(match_entry)
                match_count += 1

        db.session.commit()
        print(f"\n🎉 Seed complete!")
        print(f"   📋 {pit_count} pit scouting entries")
        print(f"   🏟️  {match_count} match scouting entries")
        print(f"   🤖 {len(teams)} teams with data")
        print(f"   🏆 Event: {event.name}")


if __name__ == '__main__':
    seed()
