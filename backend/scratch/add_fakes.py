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
            {"name": "Jean Dupont", "email": "jean.dupont@example.com"},
            {"name": "Marie Curie", "email": "marie.curie@example.com"},
            {"name": "Pierre Martin", "email": "pierre.martin@example.com"},
            {"name": "Sophie Legrand", "email": "sophie.legrand@example.com"}
        ]
        
        for scout in fake_scouts:
            # Check if exists
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
        print("Successfully added 4 fake accounts to team 1.")

if __name__ == "__main__":
    add_fake_scouts()
