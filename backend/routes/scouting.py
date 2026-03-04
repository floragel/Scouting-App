import os
import uuid
import base64
from flask import Blueprint, request, jsonify, session, abort
from werkzeug.utils import secure_filename
from models import db, Team, Event, PitScoutData, MatchScoutData, ScoutAssignment, User
from frc_api import TBAHandler

scouting_bp = Blueprint('scouting', __name__)

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
PITS_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'pit_photos')
STRATEGY_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'strategies')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@scouting_bp.route('/submit/pit', methods=['POST'])
def submit_pit_data():
    try:
        team_id = request.form.get('team_id')
        event_id = request.form.get('event_id')
        drivetrain_type = request.form.get('drivetrain_type')
        weight = request.form.get('weight')
        notes = request.form.get('notes')

        if not team_id or not event_id:
            abort(400, description="team_id and event_id are required fields")

        photo_path = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"t{team_id}_e{event_id}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                file.save(file_path)
                photo_path = os.path.join('uploads', 'pit_photos', unique_filename)

        pit_data = PitScoutData(
            team_id=int(team_id),
            event_id=int(event_id),
            drivetrain_type=drivetrain_type,
            weight=float(weight) if weight else None,
            notes=notes,
            photo_path=photo_path
        )

        db.session.add(pit_data)
        db.session.commit()

        return jsonify({'message': 'Pit scout data submitted successfully', 'data': pit_data.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        if "UNIQUE constraint failed" in str(e):
            abort(400, description="Pit scout data for this team at this event already exists.")
        abort(500, description=str(e))

@scouting_bp.route('/submit/match', methods=['POST'])
def submit_match_data():
    try:
        data = request.get_json()
        if not data:
            abort(400, description="No JSON data provided")

        required_fields = ['team_id', 'event_id', 'match_number']
        for field in required_fields:
            if field not in data:
                abort(400, description=f"Missing required field: {field}")

        match_data = MatchScoutData(
            team_id=data['team_id'],
            event_id=data['event_id'],
            match_number=data['match_number'],
            auto_balls_scored=data.get('auto_points', 0),
            teleop_balls_shot=data.get('teleop_points', 0),
            endgame_climb=data.get('climb_status', 'None'),
            notes=data.get('notes')
        )

        db.session.add(match_data)
        db.session.commit()

        return jsonify({'message': 'Match scout data submitted successfully', 'data': match_data.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        if "UNIQUE constraint failed" in str(e):
             abort(400, description="Match scout data for this team, event, and match number already exists.")
        abort(500, description=str(e))

@scouting_bp.route('/api/match-scout/upload-strategy', methods=['POST'])
def upload_strategy():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    match_id = data.get('match_id')
    image_data_b64 = data.get('image_data')

    if not match_id or not image_data_b64:
        return jsonify({'error': 'Missing match_id or image_data'}), 400

    match_data = MatchScoutData.query.get(match_id)
    if not match_data:
        return jsonify({'error': 'Match not found'}), 404

    try:
        if ',' in image_data_b64:
            image_data_b64 = image_data_b64.split(',')[1]

        img_bytes = base64.b64decode(image_data_b64)

        filename = f"strategy_match_{match_id}_{uuid.uuid4().hex[:6]}.png"
        filepath = os.path.join(STRATEGY_UPLOAD_FOLDER, filename)

        with open(filepath, 'wb') as f:
            f.write(img_bytes)

        match_data.strategy_image_url = f"/uploads/strategies/{filename}"
        db.session.commit()

        return jsonify({'message': 'Strategy saved successfully', 'url': match_data.strategy_image_url}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process strategy image: {str(e)}'}), 500

@scouting_bp.route('/api/submit-match-scout', methods=['POST'])
def submit_match_scout_web():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    try:
        assignment_id = data.get('assignment_id')
        assignment = ScoutAssignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'error': 'Invalid assignment'}), 400
            
        team = Team.query.filter_by(team_number=int(assignment.team_key.replace('frc',''))).first()
        event = Event.query.filter_by(tba_key=assignment.match_key.split('_')[0]).first()
        
        if not team or not event:
            return jsonify({'error': 'Team or Event not found in local DB'}), 400
            
        match_num_str = assignment.match_key.split('_')[1]
        match_number = int(''.join(filter(str.isdigit, match_num_str)))
        
        import json
        
        try:
            start_pos_raw = data.get('starting_position')
            starting_pos_str = json.dumps(start_pos_raw) if isinstance(start_pos_raw, dict) else str(start_pos_raw)
        except:
            starting_pos_str = "None"
            
        try:
            traj_raw = data.get('auto_trajectory')
            auto_traj_str = json.dumps(traj_raw) if isinstance(traj_raw, list) else str(traj_raw or "[]")
        except:
            auto_traj_str = "[]"
            
        match_data = MatchScoutData(
            team_id=team.id,
            event_id=event.id,
            match_number=match_number,
            starting_position=starting_pos_str,
            auto_trajectory=auto_traj_str,
            auto_start_balls=int(data.get('auto_start_balls', 0)),
            auto_balls_shot=int(data.get('auto_balls_shot', 0)),
            auto_balls_scored=int(data.get('auto_balls_scored', 0)),
            auto_climb=data.get('auto_climb', 'None'),
            teleop_intake_speed=int(data.get('teleop_intake_speed', 3)),
            teleop_shooter_accuracy=int(data.get('teleop_shooter_accuracy', 3)),
            teleop_balls_shot=int(data.get('teleop_balls_shot', 0)),
            passes_bump=data.get('passes_bump') == True or data.get('passes_bump') == 'true',
            passes_trench=data.get('passes_trench') == True or data.get('passes_trench') == 'true',
            endgame_climb=data.get('endgame_climb', 'None'),
            notes=data.get('notes', ''),
            scouter_id=session['user_id']
        )
        
        db.session.add(match_data)
        db.session.delete(assignment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Match data saved', 'match_id': match_data.id})
    except Exception as e:
        print("Error saving match data:", e)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@scouting_bp.route('/api/submit-pit-scout', methods=['POST'])
def submit_pit_scout_web():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.form
    assignment_id = data.get('assignment_id')
    team_key = data.get('team_key')
    team_name = data.get('team_name', '').strip()
    
    if not assignment_id or not team_key:
        return jsonify({'error': 'Missing required fields'}), 400
        
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    if assignment.user_id != session['user_id']:
        return jsonify({'error': 'Not your assignment'}), 403
        
    user = User.query.get(session['user_id'])
    event_id = None
    if user.team:
        event = user.team.events.first()
        if event:
            event_id = event.id
            
    if not event_id:
        tba = TBAHandler()
        status = None
        if user.team and user.team.team_number:
            status = tba.get_team_status(f"frc{user.team.team_number}")
        if status and status.get('event_key'):
            event_obj = Event.query.filter_by(tba_key=status['event_key']).first()
            if event_obj:
                event_id = event_obj.id

    team_number = int(team_key.replace('frc', ''))
    team = Team.query.filter_by(team_number=team_number).first()
    if not team:
        team = Team(tba_key=team_key, team_number=team_number, team_name=team_name or team_key)
        db.session.add(team)
        db.session.flush() 
    elif team_name and (not team.team_name or team.team_name == team.tba_key):
        team.team_name = team_name
    
    if not event_id:
        return jsonify({'error': 'Could not determine current event'}), 400

    try:
        pit_data = PitScoutData.query.filter_by(team_id=team.id, event_id=event_id).first()
        if not pit_data:
            pit_data = PitScoutData(team_id=team.id, event_id=event_id)
            db.session.add(pit_data)
            
        photo_path = ''
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '':
                import time
                filename = secure_filename(file.filename)
                unique_filename = f"t{team_key}_{int(time.time())}_{filename}"
                upload_path = os.path.join(basedir, 'static', 'uploads', 'pit_photos')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, unique_filename))
                photo_path = f"/static/uploads/pit_photos/{unique_filename}"
                
        pit_data.drivetrain_type = data.get('drivetrain_type', 'Swerve')
        pit_data.weight = float(data.get('weight', 0) if data.get('weight') else 0)
        pit_data.motor_type = data.get('motor_type', 'Kraken X60')
        pit_data.motor_count = int(data.get('motor_count', 4) if data.get('motor_count') else 4)
        pit_data.dimensions_l = float(data.get('dim_l', 0) if data.get('dim_l') else 0)
        pit_data.dimensions_w = float(data.get('dim_w', 0) if data.get('dim_w') else 0)
        pit_data.max_fuel_capacity = int(data.get('max_fuel', 50) if data.get('max_fuel') else 50)
        pit_data.climb_level = data.get('climb_level', 'None')
        pit_data.scoring_preference = data.get('scoring_pref', 'Both')
        pit_data.intake_type = data.get('intake_type', 'Both')
        pit_data.auto_leave = (data.get('auto_leave') == 'true')
        pit_data.auto_score_fuel = (data.get('auto_score_fuel') == 'true')
        pit_data.auto_collect_fuel = (data.get('auto_collect_fuel') == 'true')
        pit_data.auto_climb_l1 = (data.get('auto_climb_l1') == 'true')
        pit_data.auto_pickup = (data.get('auto_pickup') == 'true')
        pit_data.notes = data.get('notes', '').strip()
        
        if photo_path:
            pit_data.photo_path = photo_path
        
        db.session.delete(assignment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Pit data saved'})
    except Exception as e:
        print("Error saving pit data:", e)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
