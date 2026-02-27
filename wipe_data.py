import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from backend.app import app, db, MatchScoutData, PitScoutData

with app.app_context():
    print("Deleting all Match data...")
    db.session.query(MatchScoutData).delete()
    print("Deleting all Pit data...")
    db.session.query(PitScoutData).delete()
    db.session.commit()
    print("Database data successfully wiped!")
