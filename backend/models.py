from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

# Association Table for Many-to-Many relationship between Events and Teams
event_team = db.Table('event_team',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(50), default='pending') # e.g. Admin, Head Scout, Pit Scout, pending
    status = db.Column(db.String(50), default='pending') # e.g. active, pending
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    # Relationship to ScoutAssignment
    assignments = db.relationship('ScoutAssignment', backref='user', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'profile_picture': self.profile_picture,
            'role': self.role,
            'status': self.status,
            'team_id': self.team_id,
            'team_number': self.team.team_number if self.team else None,
            'team_access_code': self.team.access_code if self.team else None
        }

class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    tba_key = db.Column(db.String(50), unique=True) # The Blue Alliance key, e.g. 2024casj
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    date = db.Column(db.String(50))
    status = db.Column(db.String(50)) # e.g., 'completed', 'ongoing', 'upcoming'
    
    # Relationship to Teams
    teams = db.relationship('Team', secondary=event_team, backref=db.backref('events', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'tba_key': self.tba_key,
            'name': self.name,
            'location': self.location,
            'date': self.date,
            'status': self.status,
            'teams': [{'number': str(t.team_number), 'nickname': t.nickname} for t in self.teams]
        }

class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, primary_key=True)
    tba_key = db.Column(db.String(50), unique=True) # e.g. frc254
    team_number = db.Column(db.Integer, unique=True, nullable=False)
    team_name = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(100))
    access_code = db.Column(db.String(50), nullable=True) # For onboarding
    
    # Relationship to Users
    users = db.relationship('User', backref='team', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tba_key': self.tba_key,
            'team_number': self.team_number,
            'team_name': self.team_name,
            'nickname': self.nickname
        }

class PitScoutData(db.Model):
    __tablename__ = 'pit_scout_data'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    
    drivetrain_type = db.Column(db.String(50))
    weight = db.Column(db.Float)
    notes = db.Column(db.Text)
    photo_path = db.Column(db.String(255))
    
    # Ensure one pit scout entry per team per event
    __table_args__ = (UniqueConstraint('team_id', 'event_id', name='_team_event_pit_uc'),)
    
    # Relationships to Team and Event models
    team = db.relationship('Team', backref=db.backref('pit_data', lazy=True))
    event = db.relationship('Event', backref=db.backref('pit_data', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'event_id': self.event_id,
            'drivetrain_type': self.drivetrain_type,
            'weight': self.weight,
            'notes': self.notes,
            'photo_path': self.photo_path
        }

class MatchScoutData(db.Model):
    __tablename__ = 'match_scout_data'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    match_number = db.Column(db.Integer, nullable=False)
    
    # Auto
    auto_points = db.Column(db.Integer, default=0)
    auto_tasks = db.Column(db.Integer, default=0)
    
    # Teleop
    teleop_points = db.Column(db.Integer, default=0)
    teleop_tasks = db.Column(db.Integer, default=0)
    
    # Endgame
    climb_status = db.Column(db.String(50))
    
    # General
    notes = db.Column(db.Text)
    
    # Ensure unique match data per team per match per event
    __table_args__ = (UniqueConstraint('team_id', 'event_id', 'match_number', name='_team_event_match_uc'),)
    
    # Relationships to Team and Event models
    team = db.relationship('Team', backref=db.backref('match_data', lazy=True))
    event = db.relationship('Event', backref=db.backref('match_data', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'event_id': self.event_id,
            'match_number': self.match_number,
            'auto_points': self.auto_points,
            'auto_tasks': self.auto_tasks,
            'teleop_points': self.teleop_points,
            'teleop_tasks': self.teleop_tasks,
            'climb_status': self.climb_status,
            'notes': self.notes
        }

class ScoutAssignment(db.Model):
    __tablename__ = 'scout_assignment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    match_key = db.Column(db.String(50), nullable=False) # e.g., '2026qcmo_qm1'
    team_key = db.Column(db.String(50), nullable=False)  # e.g., 'frc6622'
    alliance_color = db.Column(db.String(20)) # 'Red' or 'Blue'
    status = db.Column(db.String(50), default='Pending') # 'Pending', 'Completed'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'match_key': self.match_key,
            'team_key': self.team_key,
            'alliance_color': self.alliance_color,
            'status': self.status
        }
