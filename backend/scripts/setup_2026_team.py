import os
import sys
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DEFAULT_PASSWORD = "Stan2026!"
DEFAULT_DOMAIN = "stanrobotix.com"

# Role Mapping based on the list
TEAM_MEMBERS = [
    {"name": "Nayl", "email": "lahlou.nayl@icloud.com", "roles": "Admin, Dev Lead"},
    {"name": "Timothée", "email": "timothee@stanrobotix.com", "roles": "Dev Lead, Captain"},
    {"name": "Nina", "email": "nina@stanrobotix.com", "roles": "Captain"},
    {"name": "Alban", "email": "alban@stanrobotix.com", "roles": "Construction Lead"},
    {"name": "Danaé", "email": "danae@stanrobotix.com", "roles": "Head Scout"},
    {"name": "Jisoo", "email": "jisoo@stanrobotix.com", "roles": "Head Scout"},
    {"name": "Saulius", "email": "saulius@stanrobotix.com", "roles": "Stand Scout, Pit Scout"},
    {"name": "Lojayen", "email": "lojayen@stanrobotix.com", "roles": "Stand Scout, Pit Scout"},
    {"name": "Anna", "email": "anna@stanrobotix.com", "roles": "Pit Scout"},
    {"name": "Pierre", "email": "pierre@stanrobotix.com", "roles": "Pit Scout"},
    {"name": "Alexander", "email": "alexander@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "Raphaël A", "email": "raphael@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "Paul-Hugo", "email": "paulhugo@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "Clémence", "email": "clemence@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "Marcu", "email": "marcu@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "Julien", "email": "julien@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "Sofia", "email": "sofia@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "El Ghali", "email": "elghali@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "Noé", "email": "noe@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "James", "email": "james@stanrobotix.com", "roles": "Stand Scout"},
    {"name": "Luc", "email": "luc@stanrobotix.com", "roles": "Media"},
    {"name": "Georges", "email": "georges@stanrobotix.com", "roles": "Media"},
    {"name": "Théa", "email": "thea@stanrobotix.com", "roles": "Scout"},
    {"name": "Pauline", "email": "pauline@stanrobotix.com", "roles": "Scout"},
    {"name": "Katherine", "email": "katherine@stanrobotix.com", "roles": "Scout"}
]

def setup_team():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found!")
        return

    engine = create_engine(DATABASE_URL)
    password_hash = generate_password_hash(DEFAULT_PASSWORD)

    print(f"🚀 Updating/Creating {len(TEAM_MEMBERS)} team accounts...")

    with engine.begin() as conn:
        for member in TEAM_MEMBERS:
            # Check if user exists
            result = conn.execute(text("SELECT id FROM \"user\" WHERE email = :email"), {"email": member['email']})
            user_exists = result.fetchone()

            if user_exists:
                print(f"🔄 Correcting: {member['name']} ({member['email']})")
                conn.execute(text("""
                    UPDATE "user" 
                    SET role = :role, 
                        name = :name, 
                        status = 'active', 
                        password_plain = :password_plain, 
                        password_hash = :password_hash
                    WHERE email = :email
                """), {
                    "role": member['roles'],
                    "name": member['name'],
                    "email": member['email'],
                    "password_plain": DEFAULT_PASSWORD,
                    "password_hash": password_hash
                })
            else:
                print(f"🆕 Creating: {member['name']} ({member['email']})")
                conn.execute(text("""
                    INSERT INTO "user" (email, password_hash, password_plain, name, role, status, matches_scouted)
                    VALUES (:email, :password_hash, :password_plain, :name, :role, 'active', 0)
                """), {
                    "email": member['email'],
                    "password_hash": password_hash,
                    "password_plain": DEFAULT_PASSWORD,
                    "name": member['name'],
                    "role": member['roles']
                })

    print("\n✅ Setup verified!")
    print(f"👉 You can now login with {DEFAULT_PASSWORD}")

if __name__ == "__main__":
    setup_team()
