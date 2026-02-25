import tempfile
import os
import io
import sys
from app import app, db
from models import Event, Team, PitScoutData, MatchScoutData

def test():
    # Configure app for testing
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use in-memory db for fast testing
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            
            # Seed data
            event1 = Event(name="Regional 1", location="City A", date="2024-03-01", status="upcoming")
            team1 = Team(team_number=254, team_name="The Cheesy Poofs", nickname="Poofs")
            team2 = Team(team_number=1114, team_name="Simbotics", nickname="Simbotics")
            team3 = Team(team_number=1678, team_name="Citrus Circuits", nickname="Citrus")
            
            event1.teams.extend([team1, team2, team3])
            db.session.add_all([event1, team1, team2, team3])
            db.session.commit()
            
            print("1. Testing GET /events")
            res = client.get('/events')
            print(res.status_code, res.get_json())
            
            print("\n2. Testing GET /events/1/teams")
            res = client.get('/events/1/teams')
            print(res.status_code, len(res.get_json()), "teams retrieved")
            
            print("\n3. Testing POST /submit/pit")
            data = {
                'team_id': team1.id,
                'event_id': event1.id,
                'drivetrain_type': 'Swerve',
                'weight': '124.5',
                'notes': 'Fast boi',
                'photo': (io.BytesIO(b"fake image data"), 'robot.jpg')
            }
            res = client.post('/submit/pit', data=data, content_type='multipart/form-data')
            print(res.status_code, res.get_json())
            
            print("\n4. Testing POST /submit/match")
            match_data = {
                'team_id': team1.id,
                'event_id': event1.id,
                'match_number': 1,
                'auto_points': 20,
                'teleop_points': 50,
                'climb_status': 'Success'
            }
            res = client.post('/submit/match', json=match_data)
            print(res.status_code, res.get_json())
            
            print("\n5. Testing GET /teams/1")
            res = client.get(f'/teams/{team1.id}')
            print(res.status_code, res.get_json())
            
            print("\n6. Testing GET /api/headscout/rankings")
            res = client.get('/api/headscout/rankings')
            print(res.status_code, res.get_json())
            
            print("\n7. Testing GET /api/headscout/match-report?teams=254,1114")
            res = client.get('/api/headscout/match-report?teams=254,1114')
            print(res.status_code, res.get_json())

if __name__ == '__main__':
    test()
