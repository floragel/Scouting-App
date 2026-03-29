from app import app, db
from models import MatchScoutData, Event, User

with app.app_context():
    print("MatchScoutData count:", MatchScoutData.query.count())
    m = MatchScoutData.query.first()
    if m:
        print("First match scouter_id:", m.scouter_id)
        if m.event:
            print("Event date:", m.event.date)
