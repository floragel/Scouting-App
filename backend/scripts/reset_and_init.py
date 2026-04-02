import os
import sys
import datetime
import unicodedata
import re

# Add the backend directory to sys.path to import models and app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import db, User, Team, Event, MatchScoutData, PitScoutData, ScoutAssignment
from werkzeug.security import generate_password_hash

def slugify(name):
    """Convert name to a clean email prefix."""
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    name = name.lower().replace(' ', '.').replace('-', '.')
    return re.sub(r'[^a-zA-Z0-9.]', '', name)

def init_db():
    with app.app_context():
        print("Creating/Clearing database...")
        db.create_all()
        # Order matters for foreign keys
        ScoutAssignment.query.delete()
        MatchScoutData.query.delete()
        PitScoutData.query.delete()
        User.query.delete()
        Team.query.delete()
        Event.query.delete()
        
        db.session.commit()
        print("Database initialized and cleared.")

        # 1. Create Team 6622
        team_6622 = Team(
            team_number=6622,
            team_name="StanRobotix",
            nickname="StanRobotix",
            access_code="STAN6622",
            tba_key="frc6622"
        )
        db.session.add(team_6622)
        db.session.commit()
        print(f"Team 6622 created with access code: {team_6622.access_code}")

        # 2. Define Members
        DEFAULT_PASSWORD = "FRC6622!"
        
        MEMBER_GROUPS = {
            "Head Scout": ["Danaé", "Jisoo"],
            "Pit Scout": ["Saulius", "Lojayen", "Anna", "Pierre"],
            "Stand Scout": [
                "Alexander", "Raphaël A.", "Paul-Hugo", "Clémence", 
                "Marcu", "Julien", "Sofia", "El Ghali", "Noé", "James",
                "Luc", "George", "Théa", "Pauline"
            ]
        }

        # Also add the main Admin account
        admin_user = User(
            email="nayl.lahlou@nayl.ca",
            name="Nayl Lahlou",
            password_hash=generate_password_hash(DEFAULT_PASSWORD),
            password_plain=DEFAULT_PASSWORD,
            role="Admin",
            status="active",
            team_id=team_6622.id,
            join_date=datetime.datetime.now().strftime("%Y-%m-%d")
        )
        db.session.add(admin_user)

        # Create all other members
        for role, names in MEMBER_GROUPS.items():
            for name in names:
                email = f"{slugify(name)}@nayl.ca"
                # Check if email already exists (e.g. Lojayen might be in two lists if I'm not careful)
                if User.query.filter_by(email=email).first():
                    print(f"Skipping duplicate: {name}")
                    continue
                    
                user = User(
                    email=email,
                    name=name,
                    password_hash=generate_password_hash(DEFAULT_PASSWORD),
                    password_plain=DEFAULT_PASSWORD,
                    role=role,
                    status="active",
                    team_id=team_6622.id,
                    join_date=datetime.datetime.now().strftime("%Y-%m-%d")
                )
                db.session.add(user)
                print(f"Created {role}: {name} ({email})")

        db.session.commit()
        print("\nAll accounts created successfully!")
        print(f"Default Password: {DEFAULT_PASSWORD}")

if __name__ == "__main__":
    init_db()
