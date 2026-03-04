import os
import json
import requests
from flask import Blueprint, jsonify, session, request
from models import User, Event, MatchScoutData, PitScoutData
from .admin import check_admin
import frc_api
from frc_api import TBAHandler

picklist_bp = Blueprint('picklist', __name__)

@picklist_bp.route('/api/import/scout-data', methods=['POST'])
def import_scout_data():
    """Import JSON scouting data dumped from external sources."""
    user, err_resp, err_code = check_admin()
    if err_resp: return err_resp, err_code
    
    from flask import request
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if not file or not file.filename.endswith('.json'):
        return jsonify({'error': 'Invalid file type. Please upload a .json file.'}), 400
        
    try:
        data = json.load(file)
        
        metadata = data.get('metadata', {})
        team_key = metadata.get('team_key')
        
        if not team_key:
            return jsonify({'error': 'Invalid JSON: Missing team_key in metadata'}), 400
            
        from models import db, Team, Event, PitScoutData, MatchScoutData
        team = Team.query.filter_by(tba_key=team_key).first()
        if not team:
            team_number = int(team_key.replace('frc', ''))
            team = Team.query.filter_by(team_number=team_number).first()
            
        if not team:
            return jsonify({'error': f'Team {team_key} not found in database'}), 404

        tba = TBAHandler()
        team_status = None
        user = User.query.get(session['user_id'])
        if user.team and user.team.team_number:
            team_status = tba.get_team_status(f"frc{user.team.team_number}")
        event_key = metadata.get('event_key') or (team_status.get('event_key') if team_status else None)
        
        if not event_key:
            return jsonify({'error': 'No event context found for import'}), 400
            
        event = Event.query.filter_by(tba_key=event_key).first()
        if not event:
            return jsonify({'error': f'Event {event_key} not found in database'}), 404

        if 'technical_specs' in data: # Pit Data
            existing = PitScoutData.query.filter_by(team_id=team.id, event_id=event.id).first()
            if not existing:
                existing = PitScoutData(team_id=team.id, event_id=event.id)
                db.session.add(existing)
            
            specs = data.get('technical_specs', {})
            dims = specs.get('dimensions', {})
            compliance = data.get('game_compliance', {})
            auto = data.get('autonomous', {})
            analysis = data.get('analysis', {})
            
            existing.drivetrain_type = specs.get('drivetrain', 'Swerve')
            existing.motor_type = specs.get('motor_type', 'Kraken X60')
            existing.motor_count = specs.get('motor_count', 4)
            existing.weight = specs.get('weight_lbs', 0)
            existing.dimensions_l = dims.get('length_in', 0)
            existing.dimensions_w = dims.get('width_in', 0)
            existing.max_fuel_capacity = compliance.get('max_fuel_capacity', 50)
            existing.climb_level = compliance.get('climb_level', 'None')
            existing.intake_type = compliance.get('intake_type', 'Both')
            existing.scoring_preference = compliance.get('scoring_preference', 'Both')
            existing.auto_leave = auto.get('leave_starting_line', auto.get('leave_line', False))
            existing.auto_score_fuel = auto.get('score_fuel_hub', auto.get('score_fuel', False))
            existing.auto_collect_fuel = auto.get('collect_extra_fuel', auto.get('collect_fuel', False))
            existing.auto_climb_l1 = auto.get('climb_tower_l1', auto.get('climb_l1', False))
            existing.notes = analysis.get('notes', data.get('notes', ''))
            
        elif 'teleop' in data or 'match_metrics' in data: # Match Data
            match_key = metadata.get('match_key', 'qm0')
            match_number = int(match_key.split('_')[-1].replace('qm', '').replace('sf', '').replace('f', '') or 0)
            
            existing = MatchScoutData.query.filter_by(team_id=team.id, event_id=event.id, match_number=match_number).first()
            if not existing:
                existing = MatchScoutData(team_id=team.id, event_id=event.id, match_number=match_number)
                db.session.add(existing)
                
            auto = data.get('autonomous', {})
            teleop = data.get('teleop', {})
            endgame = data.get('endgame', {})
            
            existing.auto_start_balls = auto.get('start_balls', auto.get('starting_balls', 0))
            existing.auto_balls_shot = auto.get('balls_shot', auto.get('total_balls_shot', 0))
            existing.auto_balls_scored = auto.get('balls_scored', 0)
            existing.auto_climb = auto.get('climb', auto.get('climb_level', 'None'))
            existing.teleop_intake_speed = teleop.get('intake_speed', 3)
            existing.teleop_shooter_accuracy = teleop.get('shooter_accuracy', 3)
            existing.teleop_balls_shot = teleop.get('balls_shot', teleop.get('total_balls_shot', 0))
            existing.passes_bump = teleop.get('passes_bump', False)
            existing.passes_trench = teleop.get('passes_trench', False)
            existing.endgame_climb = endgame.get('climb', endgame.get('climb_level', 'None'))
            existing.notes = data.get('notes', '')
            existing.scouter_id = metadata.get('scout_id') or metadata.get('scouter_id')

        db.session.commit()
        return jsonify({'success': True, 'message': f'Successfully imported data for Team {team_key}'})
        
    except Exception as e:
        from models import db
        db.session.rollback()
        print(f"Import error: {e}")
        return jsonify({'error': str(e)}), 500
