import sys
import os

# Add backend to path so we can import models
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app
from models import db, User, Team

def sync_stanrobotix_users(team_number=6622, domain="@stanrobotix.com"):
    """
    Utility script to move all users with a specific domain into the home team.
    """
    with app.app_context():
        # Find the team
        team = Team.query.filter_by(team_number=team_number).first()
        if not team:
            print(f"Error: Team {team_number} not found in database.")
            return

        print(f"Syncing users for Team {team_number} (ID: {team.id})...")
        
        # Find users with matching domain or part of the name
        users_to_sync = User.query.filter(
            (User.email.like(f"%{domain}")) | 
            (User.team_id == None)
        ).all()

        count = 0
        for user in users_to_sync:
            if user.team_id != team.id:
                user.team_id = team.id
                user.status = 'active' # Auto-activate for this sync
                if not user.role:
                    user.role = "Stand Scout"
                count += 1
                print(f"  + Synced: {user.name} ({user.email})")

        if count > 0:
            db.session.commit()
            print(f"Successfully synchronized {count} users to Team {team_number}.")
        else:
            print("No new users found to synchronize.")

if __name__ == "__main__":
    # Default to Team 6622 and @stanrobotix.com
    # The user's team ID in Supabase was 23 for team 6622
    sync_stanrobotix_users(team_number=6622)
