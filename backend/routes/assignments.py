import time
import requests
from flask import Blueprint, request, jsonify, session
from models import db, User, ScoutAssignment, Team, PitScoutData, Event, MatchScoutData
from frc_api import TBAHandler, BASE_URL, HEADERS
import frc_api

assignments_bp = Blueprint('assignments', __name__)

@assignments_bp.route('/api/user/next-assignment', methods=['GET'])
def get_next_assignment():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    user = User.query.get(session['user_id'])
    next_assignment = ScoutAssignment.query.filter_by(
        user_id=user.id, 
        status='Pending'
    ).order_by(ScoutAssignment.id.asc()).first()
    
    if next_assignment:
        return jsonify({
            'has_assignment': True,
            'assignment': next_assignment.to_dict()
        })
    return jsonify({'has_assignment': False})

@assignments_bp.route('/api/import-scout-data', methods=['POST'])
def import_scout_data_api():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    queue = request.get_json()
    if not isinstance(queue, list):
        return jsonify({'success': False, 'message': 'Invalid data format'}), 400
    
    imported_count = 0
    errors = []
    
    for item in queue:
        try:
            data = item.get('data')
            if not data: continue
            
            # Identify if it's Match or Pit data
            metadata = data.get('metadata', {})
            team_key = metadata.get('team_key')
            if not team_key: continue
            
            team = Team.query.filter_by(tba_key=team_key).first()
            if not team:
                # Create team if missing
                team_num = int(team_key.replace('frc', ''))
                team = Team(tba_key=team_key, team_number=team_num, team_name=f"Team {team_num}")
                db.session.add(team)
                db.session.flush()

            # For now, we assume the first event in the system or a default one if match_key doesn't specify
            event_key = metadata.get('match_key', '').split('_')[0] if metadata.get('match_key') else '2026bcvi'
            event = Event.query.filter_by(tba_key=event_key).first()
            if not event:
                event = Event(tba_key=event_key, name=f"Event {event_key}")
                db.session.add(event)
                db.session.flush()

            if 'match_key' in metadata:
                # Match Data
                match_num_str = metadata['match_key'].split('_')[-1]
                match_num = int(''.join(filter(str.isdigit, match_num_str))) if match_num_str else 0
                
                # Check for existing
                existing = MatchScoutData.query.filter_by(team_id=team.id, event_id=event.id, match_number=match_num).first()
                if not existing:
                    auto = data.get('autonomous', {})
                    teleo = data.get('teleop', {})
                    endge = data.get('endgame', {})
                    
                    new_match = MatchScoutData(
                        team_id=team.id,
                        event_id=event.id,
                        match_number=match_num,
                        auto_start_balls=auto.get('start_balls', 0),
                        auto_balls_shot=auto.get('balls_shot', 0),
                        auto_balls_scored=auto.get('balls_scored', 0),
                        auto_climb=auto.get('climb', 'None'),
                        teleop_intake_speed=teleo.get('intake_speed', 3),
                        teleop_shooter_accuracy=teleo.get('shooter_accuracy', 3),
                        teleop_balls_shot=teleo.get('balls_shot', 0),
                        passes_bump=teleo.get('passes_bump', False),
                        passes_trench=teleo.get('passes_trench', False),
                        endgame_climb=endge.get('climb', 'None'),
                        notes=data.get('notes', ''),
                        scouter_id=metadata.get('scouter_id') or session['user_id']
                    )
                    db.session.add(new_match)
                    imported_count += 1
            else:
                # Pit Data
                existing = PitScoutData.query.filter_by(team_id=team.id, event_id=event.id).first()
                if not existing:
                    ts = data.get('technical_specs', {})
                    gc = data.get('game_compliance', {})
                    auto = data.get('autonomous', {})
                    analysis = data.get('analysis', {})
                    
                    new_pit = PitScoutData(
                        team_id=team.id,
                        event_id=event.id,
                        drivetrain_type=ts.get('drivetrain'),
                        motor_type=ts.get('motor_type'),
                        motor_count=ts.get('motor_count', 4),
                        weight=ts.get('weight_lbs'),
                        dimensions_l=ts.get('dimensions', {}).get('length_in'),
                        dimensions_w=ts.get('dimensions', {}).get('width_in'),
                        max_fuel_capacity=gc.get('max_fuel_capacity', 50),
                        climb_level=gc.get('climb_level', 'None'),
                        intake_type=gc.get('intake_type', 'None'),
                        scoring_preference=gc.get('scoring_preference', 'None'),
                        auto_leave=auto.get('leave_starting_line', False),
                        auto_score_fuel=auto.get('score_fuel_hub', False),
                        auto_collect_fuel=auto.get('collect_extra_fuel', False),
                        auto_climb_l1=auto.get('climb_tower_l1', False),
                        notes=analysis.get('notes', '')
                    )
                    db.session.add(new_pit)
                    imported_count += 1
                    
        except Exception as e:
            errors.append(str(e))
            continue
            
    db.session.commit()
    return jsonify({
        'success': True,
        'imported_count': imported_count,
        'errors': errors
    })

@assignments_bp.route('/api/search-team', methods=['GET'])
def search_team_api():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    # Search by number or nickname
    is_num = query.isdigit()
    if is_num:
        teams = Team.query.filter(Team.team_number.like(f"%{query}%")).limit(10).all()
    else:
        teams = Team.query.filter(Team.nickname.ilike(f"%{query}%")).limit(10).all()
        
    return jsonify([{'number': t.team_number, 'nickname': t.nickname, 'key': t.tba_key} for t in teams])

@assignments_bp.route('/api/event/matches', methods=['GET'])
def get_event_matches_api():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    user = User.query.get(session['user_id'])
    team_key = user.team.tba_key if (user.team and user.team.tba_key) else (f"frc{user.team.team_number}" if user.team else 'frc6622')
    
    selected_year = request.args.get('year', 2026, type=int)
    show_all = request.args.get('show_all') == 'true'
    event_matches = []
    fallback_year = None
    
    # Try to find matches for the selected year, then fallback to previous year
    years_to_try = [selected_year, selected_year - 1]
    
    for try_year in years_to_try:
        try:
            e_res = requests.get(f"{BASE_URL}/team/{team_key}/events/{try_year}/simple", headers=HEADERS, timeout=5)
            if e_res.status_code == 200 and e_res.json():
                events = sorted(e_res.json(), key=lambda x: x['end_date'], reverse=True)
                for ev in events:
                    em = frc_api.get_event_matches(ev['key'])
                    if em:
                        all_valid = [m for m in em if m.get('time')]
                        all_valid.sort(key=lambda x: x['time'])
                        if all_valid:
                            event_matches = all_valid
                            if try_year != selected_year:
                                fallback_year = try_year
                            break
            if event_matches:
                break
        except Exception as e:
            print(f"API Match error for year {try_year}: {e}")
    
    # Filter to upcoming only (unless show_all)
    total = len(event_matches)
    filtered = False
    if not show_all and event_matches:
        now = int(time.time())
        upcoming = [m for m in event_matches if m.get('time', 0) > now]
        if upcoming:
            filtered = True
            event_matches = upcoming
        # If no upcoming, show all (past matches are still useful)
    
    return jsonify({
        'matches': event_matches,
        'total': total,
        'filtered': filtered,
        'fallback_year': fallback_year
    })

@assignments_bp.route('/api/admin/auto-assign', methods=['POST'])
def auto_assign():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    if not user or user.role not in ['Admin', 'Head Scout']:
        return jsonify({'error': 'Unauthorized role'}), 403
        
    team_members = []
    if hasattr(user, 'team_id') and user.team_id:
        team_members = User.query.filter_by(team_id=user.team_id).all()
        
    if not team_members:
        team_members = User.query.all()
        
    eligible_scouts = [m for m in team_members if m.role in ['Stand Scout', 'Pit Scout', 'Strategy Lead'] and m.status == 'active']
    
    if len(eligible_scouts) < 6:
        return jsonify({'error': f'Need at least 6 active scouts. Only found {len(eligible_scouts)}.'}), 400
        
    tba = TBAHandler()
    team_key = user.team.tba_key if user.team else 'frc6622'
    team_status = tba.get_team_status(team_key)
    if not team_status or not team_status.get('event_key'):
        return jsonify({'error': 'Team not registered for an active event.'}), 400
        
    em = frc_api.get_event_matches(team_status['event_key'])
    
    # Fallback to 2025 if no matches found for current event
    if not em:
        try:
            prev_year = 2025
            res = requests.get(f"{BASE_URL}/team/{team_key}/events/{prev_year}/simple", headers=HEADERS, timeout=5)
            if res.status_code ==    200 and res.json():
                events = sorted(res.json(), key=lambda x: x['end_date'], reverse=True)
                if events:
                    em = frc_api.get_event_matches(events[0]['key'])
        except Exception as e:
            print(f"Auto-assign fallback error: {e}")

    if not em:
        return jsonify({'error': 'No matches found/scheduled for this event or previous season (2025).'}), 400
        
    upcoming_matches = [m for m in em if m.get('time')]
    upcoming_matches.sort(key=lambda x: x['time'])
    upcoming_matches = [m for m in upcoming_matches if ScoutAssignment.query.filter_by(match_key=m['key']).count() < 6]
    
    if not upcoming_matches:
        return jsonify({'error': 'No upcoming matches found to assign.'}), 400
        
    matches_to_assign = upcoming_matches[:5]
    
    scout_stats = {
        s.id: {
            'total_assigned': ScoutAssignment.query.filter_by(user_id=s.id).count(),
            'consecutive': 0,
            'teams_scouted': set([d.team_key for d in ScoutAssignment.query.filter_by(user_id=s.id).all()])
        } for s in eligible_scouts
    }
    
    assignments_created = 0
    
    for match in matches_to_assign:
        existing = ScoutAssignment.query.filter_by(match_key=match['key']).count()
        if existing >= 6:
            continue
            
        teams = match['alliances']['red']['team_keys'] + match['alliances']['blue']['team_keys']
        sorted_scouts = sorted(
            eligible_scouts, 
            key=lambda s: scout_stats[s.id]['total_assigned'] + (scout_stats[s.id]['consecutive'] * 2)
        )
        
        assigned_to_this_match = set()
        
        for team_key in teams:
            alliance_color = 'Red' if team_key in match['alliances']['red']['team_keys'] else 'Blue'
            if ScoutAssignment.query.filter_by(match_key=match['key'], team_key=team_key).first():
                continue
                
            best_scout = None
            for scout in sorted_scouts:
                if scout.id in assigned_to_this_match:
                    continue
                if team_key in scout_stats[scout.id]['teams_scouted'] and len([s for s in sorted_scouts if s.id not in assigned_to_this_match]) > 1:
                    next_idx = sorted_scouts.index(scout) + 1
                    if next_idx < len(sorted_scouts) and team_key not in scout_stats[sorted_scouts[next_idx].id]['teams_scouted']:
                        continue 
                        
                best_scout = scout
                break
                
            if best_scout:
                new_assignment = ScoutAssignment(
                    user_id=best_scout.id,
                    match_key=match['key'],
                    team_key=team_key,
                    alliance_color=alliance_color
                )
                db.session.add(new_assignment)
                assigned_to_this_match.add(best_scout.id)
                
                scout_stats[best_scout.id]['total_assigned'] += 1
                scout_stats[best_scout.id]['consecutive'] += 1
                scout_stats[best_scout.id]['teams_scouted'].add(team_key)
                assignments_created += 1
        
        for s in eligible_scouts:
            if s.id not in assigned_to_this_match:
                scout_stats[s.id]['consecutive'] = 0
                
    db.session.commit()
    return jsonify({
        'success': True, 
        'message': f'Successfully auto-assigned {assignments_created} scout slots across upcoming matches.'
    })

@assignments_bp.route('/api/admin/assignments', methods=['POST'])
def create_assignment():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin_user = User.query.get(session['user_id'])
    if not admin_user or admin_user.role not in ['Admin', 'Head Scout']:
        return jsonify({'error': 'Forbidden'}), 403
        
    data = request.json
    required_fields = ['user_id', 'match_key', 'team_key', 'alliance_color']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        new_assignment = ScoutAssignment(
            user_id=data['user_id'],
            match_key=data['match_key'],
            team_key=data['team_key'],
            alliance_color=data['alliance_color'],
            status='Pending'
        )
        db.session.add(new_assignment)
        db.session.commit()
        return jsonify({'message': 'Assignment created successfully', 'assignment': new_assignment.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/api/admin/assign-pit', methods=['POST'])
def create_pit_assignment():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    admin_user = User.query.get(session['user_id'])
    if not admin_user or admin_user.role not in ['Admin', 'Head Scout']:
        return jsonify({'error': 'Forbidden'}), 403
        
    data = request.json
    required_fields = ['user_id', 'team_key']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        new_assignment = ScoutAssignment(
            user_id=data['user_id'],
            assignment_type='Pit',
            match_key='',
            team_key=data['team_key'],
            alliance_color='',
            status='Pending'
        )
        db.session.add(new_assignment)
        db.session.commit()
        return jsonify({'message': 'Pit Assignment created successfully', 'assignment': new_assignment.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/api/admin/auto-assign-pit', methods=['POST'])
def auto_assign_pit():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    if not user or user.role not in ['Admin', 'Head Scout']:
        return jsonify({'error': 'Unauthorized role'}), 403
        
    team_members = []
    if hasattr(user, 'team_id') and user.team_id:
        team_members = User.query.filter_by(team_id=user.team_id).all()
    if not team_members:
        team_members = User.query.all()
        
    pit_scouts = [m for m in team_members if m.role == 'Pit Scout' and m.status == 'active']
    
    if not pit_scouts:
        return jsonify({'error': 'No active Pit Scouts found.'}), 400
        
    tba = TBAHandler()
    team_key = user.team.tba_key if user.team else 'frc6622'
    team_status = tba.get_team_status(team_key)
    if not team_status or not team_status.get('event_key'):
        return jsonify({'error': 'Team not registered for an active event.'}), 400
        
    event_teams = frc_api.get_teams_for_event(team_status['event_key'])
    if not event_teams:
        return jsonify({'error': 'No teams found for the current event.'}), 400
        
    unassigned_teams = []
    for team in event_teams:
        existing = ScoutAssignment.query.filter_by(team_key=team['key'], assignment_type='Pit').first()
        if not existing:
            team_number = int(team['key'].replace('frc', ''))
            team_obj = Team.query.filter_by(team_number=team_number).first()
            if team_obj:
                pit_data = PitScoutData.query.filter_by(team_id=team_obj.id).first()
                if pit_data:
                    continue
            unassigned_teams.append(team)

    if not unassigned_teams:
        return jsonify({'error': 'All teams have already been assigned or scouted for pit data.'}), 400

    assignments_created = 0
    for i, team in enumerate(unassigned_teams):
        scout = pit_scouts[i % len(pit_scouts)]
        new_assignment = ScoutAssignment(
            user_id=scout.id,
            match_key='',
            team_key=team['key'],
            alliance_color='',
            assignment_type='Pit',
            status='Pending'
        )
        db.session.add(new_assignment)
        assignments_created += 1

    try:
        db.session.commit()
        return jsonify({'message': f'Successfully assigned {assignments_created} teams to {len(pit_scouts)} Pit Scouts.', 'count': assignments_created}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/api/admin/assignments/all', methods=['DELETE'])
def delete_all_assignments():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    admin_user = User.query.get(session['user_id'])
    if not admin_user or admin_user.role not in ['Admin', 'Head Scout']:
        return jsonify({'error': 'Forbidden'}), 403
        
    try:
        ScoutAssignment.query.delete()
        db.session.commit()
        return jsonify({'message': 'All assignments revoked successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/api/admin/assignments/<int:assignment_id>', methods=['DELETE'])
def delete_assignment(assignment_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    admin_user = User.query.get(session['user_id'])
    if not admin_user or admin_user.role not in ['Admin', 'Head Scout']:
        return jsonify({'error': 'Forbidden'}), 403
        
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    try:
        db.session.delete(assignment)
        db.session.commit()
        return jsonify({'message': 'Assignment deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
