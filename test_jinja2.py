import requests
import sqlite3
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Provide an assignment
conn = sqlite3.connect('backend/instance/scouting.db')
cursor = conn.cursor()

# Get scout ID
cursor.execute("SELECT id FROM user WHERE role='pending' OR role='scout' LIMIT 1")
scout_row = cursor.fetchone()
if not scout_row:
    cursor.execute("INSERT INTO user (email, password_hash, name, role) VALUES ('scout@frc.com', 'hash', 'Scout User', 'scout')")
    scout_id = cursor.lastrowid
else:
    scout_id = scout_row[0]

# Add assignment
cursor.execute("DELETE FROM scout_assignment WHERE user_id=?", (scout_id,))
cursor.execute("INSERT INTO scout_assignment (user_id, match_key, team_key, alliance_color, status) VALUES (?, '2026mtt_qm5', 'frc1234', 'Red', 'Pending')", (scout_id,))
conn.commit()
conn.close()

# 2. Login as the scout
base_url = 'http://localhost:5002'
session = requests.Session()

try:
    # Get the email
    conn = sqlite3.connect('backend/instance/scouting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM user WHERE id=?", (scout_id,))
    scout_email = cursor.fetchone()[0]
    conn.close()
    
    # We don't have the original password so let's just make a new one or use the API directly to login if possible.
    # Actually, it's easier to just recreate the user with known password
    conn = sqlite3.connect('backend/instance/scouting.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user WHERE email='known_scout@frc.com'")
    conn.commit()
    conn.close()
    
    session.post(f"{base_url}/api/auth/register", json={"email": "known_scout@frc.com", "password": "password123", "name": "Known Scout"})
    
    # Re-assign to known_scout
    conn = sqlite3.connect('backend/instance/scouting.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user WHERE email='known_scout@frc.com'")
    known_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO scout_assignment (user_id, match_key, team_key, alliance_color, status) VALUES (?, '2026mtt_qm5', 'frc1234', 'Red', 'Pending')", (known_id,))
    conn.commit()
    conn.close()

    session.post(f"{base_url}/api/auth/login", json={"email": "known_scout@frc.com", "password": "password123"})
    
    res = session.get(f"{base_url}/scout-dashboard")
    print(f"Scout Dashboard Response: {res.status_code}")
    
    if "frc1234" in res.text and "Red" in res.text:
         print("SUCCESS: Scout Assignments rendered correctly.")
    else:
         print("FAIL: Scout Assignments missing from HTML.")
         print(res.text[:500]) # Preview
         
    if "Qual" not in res.text and "Next Match" not in res.text and "Last Match" not in res.text and "TBA" not in res.text:
         print("FAIL: TBA Widget missing from HTML.")
    else:
         print("SUCCESS: TBA Widget rendered.")

except Exception as e:
    print(f"Test Failed: {e}")
