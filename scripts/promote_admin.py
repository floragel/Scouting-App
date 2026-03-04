import argparse, secrets, string
import sys
import os

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import app, db
from models import User, Team

def promote_user(email, team_number):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Error: User with email '{email}' not found.")
            return
            
        team = Team.query.filter_by(team_number=team_number).first()
        if not team:
            # Create a placeholder team if it doesn't exist
            new_code = f"{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))}{team_number}"
            team = Team(team_number=team_number, name=f"Team {team_number}", location="Unknown", access_code=new_code)
            db.session.add(team)
            db.session.commit()
            print(f"Created Team {team_number} automatically with access code: {new_code}")
        
        user.role = 'Admin'
        user.status = 'active'
        user.team_id = team.id
        db.session.commit()
        print(f"Success! '{email}' is now an Admin and Active for Team {team_number}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote a user to Admin")
    parser.add_argument("email", help="The email of the user to promote")
    parser.add_argument("team_number", type=int, help="The team number this admin should manage")
    args = parser.parse_args()
    
    promote_user(args.email, args.team_number)
