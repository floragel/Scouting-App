import os
import uuid
import base64
from flask import Blueprint, request, jsonify, session, abort
import cloudinary
import cloudinary.uploader
import datetime
from models import db, Team, Event, PitScoutData, MatchScoutData, ScoutAssignment, User
from frc_api import TBAHandler

scouting_bp = Blueprint('scouting', __name__)

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
                try:
                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder="pits",
                        public_id=f"t{team_id}_e{event_id}_{int(datetime.datetime.now().timestamp())}",
                        overwrite=True
                    )
                    photo_path = upload_result['secure_url']
                except Exception as e:
                    print(f"Cloudinary upload error: {e}")
                    abort(500, description=f"Cloudinary upload failed: {str(e)}")

        pit_data = PitScoutData(
            team_id=int(team_id),
            event_id=int(event_id),
            drivetrain_type=drivetrain_type,
            weight=float(weight) if weight else None,
            notes=notes,
            photo_path=photo_path,
            scouter_id=session.get('user_id')
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
            notes=data.get('notes'),
            scouter_id=session.get('user_id')
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

        try:
            upload_result = cloudinary.uploader.upload(
                img_bytes,
                folder="strategies",
                public_id=f"strategy_match_{match_id}_{int(datetime.datetime.now().timestamp())}",
                overwrite=True
            )
            match_data.strategy_image_url = upload_result['secure_url']
            db.session.commit()
            return jsonify({'message': 'Strategy saved successfully', 'url': match_data.strategy_image_url}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to process strategy image: {str(e)}'}), 500

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
            return jsonify({'error': 'Assignment not found or already completed'}), 400
            
        team = Team.query.filter_by(team_number=int(assignment.team_key.replace('frc',''))).first()
        
        # Try to find event from match_key (format: eventkey_matchtype)
        event = None
        if '_' in (assignment.match_key or ''):
            event_tba_key = assignment.match_key.split('_')[0]
            event = Event.query.filter_by(tba_key=event_tba_key).first()
        
        # Fallback: use most recent event
        if not event:
            event = Event.query.order_by(Event.date.desc()).first()
        
        if not team or not event:
            return jsonify({'error': 'Team or Event not found in local DB'}), 400
            
        match_num_str = assignment.match_key.split('_')[1] if '_' in assignment.match_key else assignment.match_key
        match_number = int(''.join(filter(str.isdigit, match_num_str)) or '0')
        
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
            
        # Check if match data already exists for this team at this event/match
        match_data = MatchScoutData.query.filter_by(
            team_id=team.id,
            event_id=event.id,
            match_number=match_number
        ).first()

        if not match_data:
            match_data = MatchScoutData(
                team_id=team.id,
                event_id=event.id,
                match_number=match_number
            )
            db.session.add(match_data)

        # Update fields (Upsert logic)
        match_data.starting_position = starting_pos_str
        match_data.auto_trajectory = auto_traj_str
        match_data.auto_start_balls = int(data.get('auto_start_balls', 0))
        match_data.auto_balls_shot = int(data.get('auto_balls_shot', 0))
        match_data.auto_balls_scored = int(data.get('auto_balls_scored', 0))
        match_data.auto_climb = data.get('auto_climb', 'None')
        match_data.teleop_intake_speed = int(data.get('teleop_intake_speed', 3))
        match_data.teleop_shooter_accuracy = int(data.get('teleop_shooter_accuracy', 3))
        match_data.teleop_balls_shot = int(data.get('teleop_balls_shot', 0))
        match_data.passes_bump = data.get('passes_bump') == True or data.get('passes_bump') == 'true'
        match_data.passes_trench = data.get('passes_trench') == True or data.get('passes_trench') == 'true'
        match_data.endgame_climb = data.get('endgame_climb', 'None')
        match_data.notes = data.get('notes', '')

        # Set scouter_id safely
        try:
            match_data.scouter_id = session['user_id']
        except Exception:
            pass

        # Clear all assignments for this match and team
        ScoutAssignment.query.filter_by(
            match_key=assignment.match_key,
            team_key=assignment.team_key
        ).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Match data saved', 'match_id': match_data.id})
    except Exception as e:
        import traceback
        traceback.print_exc()
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
        
    assignment = ScoutAssignment.query.get(assignment_id)
    if not assignment:
        return jsonify({'error': 'Assignment not found or already completed'}), 404
    if assignment.user_id != session['user_id']:
        return jsonify({'error': 'Not your assignment'}), 403
        
    user = User.query.get(session['user_id'])
    
    # Find the event - try multiple strategies
    event_id = None
    try:
        if user.team:
            # Strategy 1: Get events from the team's event_team relationship
            event = user.team.events.first()
            if event:
                event_id = event.id
    except Exception as e:
        print(f"Event lookup strategy 1 failed: {e}")
    
    if not event_id:
        try:
            # Strategy 2: Find any ongoing/recent event from TBA
            tba = TBAHandler()
            if user.team and user.team.team_number:
                status = tba.get_team_status(f"frc{user.team.team_number}")
                if status and status.get('event_key'):
                    event_obj = Event.query.filter_by(tba_key=status['event_key']).first()
                    if event_obj:
                        event_id = event_obj.id
        except Exception as e:
            print(f"Event lookup strategy 2 (TBA) failed: {e}")
    
    if not event_id:
        try:
            # Strategy 3: Just use the most recent event in the DB
            latest_event = Event.query.order_by(Event.date.desc()).first()
            if latest_event:
                event_id = latest_event.id
        except Exception as e:
            print(f"Event lookup strategy 3 (latest) failed: {e}")

    team_number = int(team_key.replace('frc', ''))
    team = Team.query.filter_by(team_number=team_number).first()
    if not team:
        team = Team(tba_key=team_key, team_number=team_number, team_name=team_name or team_key)
        db.session.add(team)
        db.session.flush() 
    elif team_name and (not team.team_name or team.team_name == team.tba_key):
        team.team_name = team_name
    
    if not event_id:
        return jsonify({'error': 'Could not determine current event. Please ensure at least one event exists.'}), 400

    # Check if pit data already exists for this team at this event
    pit_data = PitScoutData.query.filter_by(team_id=team.id, event_id=event_id).first()

    try:
        if not pit_data:
            pit_data = PitScoutData(team_id=team.id, event_id=event_id)
            db.session.add(pit_data)
            
        def safe_set(obj, attr, val):
            if hasattr(obj, attr):
                setattr(obj, attr, val)

        # Set scouter_id safely
        safe_set(pit_data, 'scouter_id', session['user_id'])
            
        photo_path = ''
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '':
                try:
                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder="pit_photos",
                        public_id=f"t{team_key}_{int(datetime.datetime.now().timestamp())}",
                        overwrite=True
                    )
                    photo_path = upload_result['secure_url']
                except Exception as e:
                    print(f"Cloudinary upload error: {e}")
                
        safe_set(pit_data, 'drivetrain_type', data.get('drivetrain_type', 'Swerve'))
        safe_set(pit_data, 'weight', float(data.get('weight', 0) if data.get('weight') else 0))
        safe_set(pit_data, 'motor_type', data.get('motor_type', 'Kraken X60'))
        safe_set(pit_data, 'motor_count', int(data.get('motor_count', 4) if data.get('motor_count') else 4))
        safe_set(pit_data, 'dimensions_l', float(data.get('dim_l', 0) if data.get('dim_l') else 0))
        safe_set(pit_data, 'dimensions_w', float(data.get('dim_w', 0) if data.get('dim_w') else 0))
        safe_set(pit_data, 'max_fuel_capacity', int(data.get('max_fuel', 50) if data.get('max_fuel') else 50))
        safe_set(pit_data, 'climb_level', data.get('climb_level', 'None'))
        safe_set(pit_data, 'scoring_preference', data.get('scoring_pref', 'Both'))
        safe_set(pit_data, 'intake_type', data.get('intake_type', 'Both'))
        safe_set(pit_data, 'auto_leave', (data.get('auto_leave') == 'true'))
        safe_set(pit_data, 'auto_score_fuel', (data.get('auto_score_fuel') == 'true'))
        safe_set(pit_data, 'auto_collect_fuel', (data.get('auto_collect_fuel') == 'true'))
        safe_set(pit_data, 'auto_climb_l1', (data.get('auto_climb_l1') == 'true'))
        safe_set(pit_data, 'auto_pickup', (data.get('auto_pickup') == 'true'))
        safe_set(pit_data, 'notes', data.get('notes', '').strip())
        
        if photo_path:
            safe_set(pit_data, 'photo_path', photo_path)
        
        # Clear all pit assignments for this team (for both members of a pair)
        ScoutAssignment.query.filter_by(
            team_key=assignment.team_key,
            assignment_type='Pit'
        ).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Pit data saved'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': f"Database error: {str(e)}"}), 500

@scouting_bp.route('/api/import-scout-data', methods=['POST'])
def import_scout_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data_list = request.json
    if not isinstance(data_list, list):
        data_list = [data_list]
        
    success_count = 0
    errors = []
    
    for item in data_list:
        try:
            data = item.get('data')
            if not data: continue
            
            metadata = data.get('metadata', {})
            team_key = metadata.get('team_key')
            if not team_key: continue
            
            team_number = int(team_key.replace('frc', ''))
            team = Team.query.filter_by(team_number=team_number).first()
            if not team:
                team = Team(tba_key=team_key, team_number=team_number, team_name=f"Team {team_number}")
                db.session.add(team)
                db.session.flush()
            
            # Use event from metadata or fallback to first event
            event_key = metadata.get('event_key')
            if not event_key and metadata.get('match_key'):
                event_key = metadata.get('match_key').split('_')[0]
            
            if event_key:
                event = Event.query.filter_by(tba_key=event_key).first()
            else:
                event = Event.query.first() # Fallback
                
            if not event:
                # If no event in DB, we can't really save it properly without more info
                # But let's try to create a placeholder if it's 2026
                if event_key:
                    event = Event(tba_key=event_key, name=f"Event {event_key}", year=2026)
                    db.session.add(event)
                    db.session.flush()
                else:
                    errors.append(f"Could not determine event for team {team_number}")
                    continue

            if data.get('pit_data') or (data.get('technical_specs') and data.get('game_compliance')):
                # Pit Data Import
                p = data.get('pit_data') or data
                tech = p.get('technical_specs', {})
                game = p.get('game_compliance', {})
                
                existing = PitScoutData.query.filter_by(team_id=team.id, event_id=event.id).first()
                if not existing:
                    existing = PitScoutData(team_id=team.id, event_id=event.id)
                    db.session.add(existing)
                
                # Update Pit Data (UPSERT)
                existing.drivetrain_type = tech.get('drivetrain', 'Swerve')
                existing.motor_type = tech.get('motor_type', 'Kraken X60')
                existing.motor_count = int(tech.get('motor_count', 4))
                existing.weight = float(tech.get('weight_lbs', 0))
                existing.max_fuel_capacity = int(game.get('max_fuel_capacity', 50))
                existing.climb_level = game.get('climb_level', 'None')
                existing.notes = data.get('analysis', {}).get('notes', '')
                success_count += 1
            elif data.get('match_data') or (data.get('autonomous') and data.get('teleop')):
                # Match Data Import
                m = data.get('match_data') or data
                auto = m.get('autonomous', {})
                tele = m.get('teleop', {})
                endgame = m.get('endgame', {})
                match_num_raw = metadata.get('match_number') or metadata.get('match_key', '0').split('_')[-1]
                match_num_str = ''.join(filter(str.isdigit, str(match_num_raw) or '0'))
                match_num = int(match_num_str) if match_num_str else 0 # Default to 0 instead of crashing
                
                existing = MatchScoutData.query.filter_by(team_id=team.id, event_id=event.id, match_number=match_num).first()
                if not existing:
                    existing = MatchScoutData(
                        team_id=team.id,
                        event_id=event.id,
                        match_number=match_num
                    )
                    db.session.add(existing)

                # Update Match Data (UPSERT)
                existing.auto_start_balls = int(auto.get('start_balls', 0))
                existing.auto_balls_shot = int(auto.get('balls_shot', 0))
                existing.auto_balls_scored = int(auto.get('balls_scored', 0))
                existing.teleop_intake_speed = int(tele.get('intake_speed', 3))
                existing.teleop_shooter_accuracy = int(tele.get('shooter_accuracy', 3))
                existing.teleop_balls_shot = int(tele.get('balls_shot', 0))
                existing.endgame_climb = endgame.get('climb', 'None')
                existing.notes = m.get('notes', '')
                
                # Set scouter_id safely
                try:
                    existing.scouter_id = metadata.get('scouter_id') or session['user_id']
                except Exception:
                    pass
                    
                success_count += 1
                    
        except Exception as e:
            errors.append(str(e))
            continue
            
    db.session.commit()
    return jsonify({
        'success': True, 
        'imported_count': success_count, 
        'errors': errors
    })
