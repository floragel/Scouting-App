import sys
import os

# Set up to import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.app import app, db, MatchScoutData, Team, PitScoutData

with app.app_context():
    teams = Team.query.all()
    print("Teams:", [t.tba_key for t in teams])
    matches = MatchScoutData.query.all()
    print("MATCHES:", len(matches))
    for m in matches:
        team = Team.query.get(m.team_id)
        team_key = team.tba_key if team else "None"
        print(f"Match: id={m.id}, team={team_key}, match_num={m.match_number}")
