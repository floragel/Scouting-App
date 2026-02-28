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
    motor_type = db.Column(db.String(100))
    motor_count = db.Column(db.Integer, default=4)
    dimensions_l = db.Column(db.Float)
    dimensions_w = db.Column(db.Float)
    auto_leave = db.Column(db.Boolean, default=False)
    auto_score_fuel = db.Column(db.Boolean, default=False)
    auto_collect_fuel = db.Column(db.Boolean, default=False)
    auto_climb_l1 = db.Column(db.Boolean, default=False)
    
    max_fuel_capacity = db.Column(db.Integer, default=50)
    climb_level = db.Column(db.String(20), default='None')   # None, L1, L2, L3
    scoring_preference = db.Column(db.String(20), default='None') # Low, High, Both
    intake_type = db.Column(db.String(20), default='None')   # Ground, Chute, Both

    # Keep auto_pickup as alias or legacy if needed
    auto_pickup = db.Column(db.Boolean, default=False)
    
    # 2025/2026 early-season placeholders (to be cleaned up if unused)
    auto_coral = db.Column(db.Boolean, default=False)
    auto_algae = db.Column(db.Boolean, default=False)
    
    # Legacy/Misc fields
    fits_under_trench = db.Column(db.Boolean, default=False)
    target_tower_level = db.Column(db.String(50), default='None')
    fuel_capacity = db.Column(db.Integer, default=0)
    
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
            'team_number': self.team.team_number if self.team else self.team_id,
            'event_id': self.event_id,
            'drivetrain_type': self.drivetrain_type,
            'weight': self.weight,
            'motor_type': self.motor_type,
            'motor_count': self.motor_count,
            'dimensions_l': self.dimensions_l,
            'dimensions_w': self.dimensions_w,
            'auto_leave': self.auto_leave,
            'auto_score_fuel': self.auto_score_fuel,
            'auto_collect_fuel': self.auto_collect_fuel,
            'auto_climb_l1': self.auto_climb_l1,
            'max_fuel_capacity': self.max_fuel_capacity,
            'climb_level': self.climb_level,
            'scoring_preference': self.scoring_preference,
            'intake_type': self.intake_type,
            'fits_under_trench': self.fits_under_trench,
            'target_tower_level': self.target_tower_level,
            'fuel_capacity': self.fuel_capacity,
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
    starting_position = db.Column(db.String(255), default='None') # JSON coordinates {x: int, y: int}
    auto_trajectory = db.Column(db.Text, nullable=True)     # JSON array of drawing paths
    auto_start_balls = db.Column(db.Integer, default=0)     # balles internes au debut
    auto_balls_shot = db.Column(db.Integer, default=0)      # balles total shootées (auto)
    auto_balls_scored = db.Column(db.Integer, default=0)    # balles qui rentrent (auto)
    auto_climb = db.Column(db.String(50), default='None')   # level climb auto
    
    # Teleop / Match
    teleop_intake_speed = db.Column(db.Integer, default=3)  # Numerical 0-5
    teleop_shooter_accuracy = db.Column(db.Integer, default=3) # Numerical 0-5
    teleop_balls_shot = db.Column(db.Integer, default=0)    # total balles shoot (teleop)
    passes_bump = db.Column(db.Boolean, default=False)      # si il passe la bump
    passes_trench = db.Column(db.Boolean, default=False)    # si il passe la trench
    
    # Endgame
    endgame_climb = db.Column(db.String(50), default='None') # L1 / L2 / L3
    
    # General
    notes = db.Column(db.Text)
    strategy_image_url = db.Column(db.String(255), nullable=True)
    
    # Scouter Tracking
    scouter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Ensure unique match data per team per match per event
    __table_args__ = (UniqueConstraint('team_id', 'event_id', 'match_number', name='_team_event_match_uc'),)
    
    # Relationships to Team, Event, and User models
    team = db.relationship('Team', backref=db.backref('match_data', lazy=True))
    event = db.relationship('Event', backref=db.backref('match_data', lazy=True))
    scouter = db.relationship('User', backref=db.backref('match_data', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'team_number': self.team.team_number if self.team else self.team_id,
            'event_id': self.event_id,
            'match_number': self.match_number,
            'starting_position': self.starting_position,
            'auto_trajectory': self.auto_trajectory,
            'auto_start_balls': self.auto_start_balls,
            'auto_balls_shot': self.auto_balls_shot,
            'auto_balls_scored': self.auto_balls_scored,
            'auto_climb': self.auto_climb,
            'teleop_intake_speed': self.teleop_intake_speed,
            'teleop_shooter_accuracy': self.teleop_shooter_accuracy,
            'teleop_balls_shot': self.teleop_balls_shot,
            'passes_bump': self.passes_bump,
            'passes_trench': self.passes_trench,
            'endgame_climb': self.endgame_climb,
            'notes': self.notes,
            'strategy_image_url': self.strategy_image_url,
            'scouter_id': self.scouter_id
        }

class ScoutAssignment(db.Model):
    __tablename__ = 'scout_assignment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignment_type = db.Column(db.String(20), default='Match') # 'Match' or 'Pit'
    match_key = db.Column(db.String(50), nullable=False) # e.g., '2026qcmo_qm1' (empty for pit)
    team_key = db.Column(db.String(50), nullable=False)  # e.g., 'frc6622'
    alliance_color = db.Column(db.String(20)) # 'Red' or 'Blue' (empty for pit)
    status = db.Column(db.String(50), default='Pending') # 'Pending', 'Completed'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'assignment_type': self.assignment_type,
            'match_key': self.match_key,
            'team_key': self.team_key,
            'alliance_color': self.alliance_color,
            'status': self.status
        }
