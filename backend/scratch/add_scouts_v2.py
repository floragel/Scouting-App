import sys
import os

# Set up to import app
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def add_fake_scouts():
    with app.app_context():
        # Get team ID 1 (target team)
        team_id = 1
        
        fake_scouts = [
            {"name": "Thomas Roux", "email": "thomas.roux@example.com"},
            {"name": "Camille Blanc", "email": "camille.blanc@example.com"},
            {"name": "Lucas Petit", "email": "lucas.petit@example.com"},
            {"name": "Lea Durand", "email": "lea.durand@example.com"}
        ]
        
        for scout in fake_scouts:
            if User.query.filter_by(email=scout['email']).first():
                print(f"User {scout['email']} already exists skipping.")
                continue
                
            new_user = User(
                email=scout['email'],
                name=scout['name'],
                password_hash=generate_password_hash("password123", method='pbkdf2:sha256'),
                password_plain="password123",
                team_id=team_id,
                status='active',
                role='Stand Scout'
            )
            db.session.add(new_user)
            print(f"Added {scout['name']} ({scout['email']})")
        
        db.session.commit()
        print("Successfully added 4 MORE fake accounts to team 1.")

if __name__ == "__main__":
    add_fake_scouts()
