import requests
from flask import Blueprint, jsonify, session
from models import Event, User, MatchScoutData, PitScoutData, Team
from frc_api import TBAHandler
import frc_api

briefing_bp = Blueprint('briefing', __name__)

@briefing_bp.route('/api/team_matches/<int:event_id>')
def api_team_matches(event_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    event = Event.query.get_or_404(event_id)
    if not event.tba_key:
        return jsonify({'error': 'Event has no TBA key'}), 400
        
    matches = frc_api.get_event_matches(event.tba_key)
    if not matches:
        return jsonify([])
        
    user = User.query.get(session['user_id'])
    home_team_tba_key = f"frc{user.team.team_number}" if user.team and user.team.team_number else None
    
    team_matches = []
    for m in matches:
        red_teams = m.get('alliances', {}).get('red', {}).get('team_keys', [])
        blue_teams = m.get('alliances', {}).get('blue', {}).get('team_keys', [])
        
        if home_team_tba_key and (home_team_tba_key in red_teams or home_team_tba_key in blue_teams):
            comp_level = m.get('comp_level', '').upper()
            match_num = m.get('match_number', 0)
            set_num = m.get('set_number', 1)
            
            if comp_level == 'QM':
                name = f"QM {match_num}"
            else:
                name = f"{comp_level} {set_num}-{match_num}"
                
            short_key = m['key'].split('_')[-1]
            
            team_matches.append({
                'key': short_key,
                'name': name,
                'time': m.get('time', 0) or 0
            })
            
    team_matches.sort(key=lambda x: x['time'] if x['time'] is not None else 0)
    return jsonify(team_matches)

@briefing_bp.route('/api/briefing/<int:event_id>/<match_key>')
def api_briefing(event_id, match_key):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    event = Event.query.get_or_404(event_id)
    if not event.tba_key:
        return jsonify({'error': 'Event has no TBA key'}), 400
        
    tba = TBAHandler()
    match_url = f"{frc_api.BASE_URL}/match/{event.tba_key}_{match_key}"
    res = requests.get(match_url, headers=tba.headers, timeout=5)
    
    if res.status_code != 200:
        return jsonify({'error': f'Match not found on TBA (Code {res.status_code})'}), 404
        
    match_data_tba = res.json()
    alliances = match_data_tba.get('alliances', {})
    if not alliances:
        return jsonify({'error': 'No alliance data found for this match'}), 404
        
    user = User.query.get(session['user_id'])
    if not user.team or not user.team.team_number:
        return jsonify({'error': 'No team assigned to user'}), 400

    red_teams = [t.replace('frc','') for t in alliances.get('red', {}).get('team_keys', [])]
    blue_teams = [t.replace('frc','') for t in alliances.get('blue', {}).get('team_keys', [])]
    
    home_team = str(user.team.team_number)
    
    if home_team in red_teams:
        our_alliance_color = 'red'
        our_teams = red_teams
        opp_teams = blue_teams
    elif home_team in blue_teams:
        our_alliance_color = 'blue'
        our_teams = blue_teams
        opp_teams = red_teams
    else:
        our_alliance_color = 'neutral'
        our_teams = red_teams
        opp_teams = blue_teams

    def get_team_intel(team_num):
        matches = MatchScoutData.query.filter_by(event_id=event.id).join(Team).filter(Team.team_number == int(team_num)).all()
        if not matches:
            matches = MatchScoutData.query.join(Team).filter(Team.team_number == int(team_num)).all()
            
        pit = PitScoutData.query.filter_by(event_id=event.id).join(Team).filter(Team.team_number == int(team_num)).first()
        if not pit:
            pit = PitScoutData.query.join(Team).filter(Team.team_number == int(team_num)).first()
            
        if not matches and not pit:
            return {'team': team_num, 'has_data': False}
            
        VAL_MAP = {'Very Slow': 1.0, 'Slow': 2.0, 'Medium': 3.0, 'Fast': 4.0, 'Very Fast': 5.0, 'None': 0.0, 'N/A': 0.0}
        def to_num(v, d):
            if v is None: return d
            if isinstance(v, (int, float)): return v
            s = str(v).strip()
            if not s: return d
            if s in VAL_MAP: return VAL_MAP[s]
            try: return float(s)
            except: return d

        mc = len(matches)
        if mc == 0:
            return {'team': team_num, 'has_data': True, 'pit_only': True, 'drivetrain': pit.drivetrain_type if pit else 'Unknown'}

        auto_scoring = sum(to_num(m.auto_balls_scored, 0) for m in matches) / mc
        teleop_scoring = sum(to_num(m.teleop_balls_shot, 0) for m in matches) / mc
        intake_speed = sum(to_num(m.teleop_intake_speed, 3) for m in matches) / mc
        accuracy = sum(to_num(m.teleop_shooter_accuracy, 3) for m in matches) / mc
        
        climbs = sum(1 for m in matches if str(m.endgame_climb).strip() not in ['None', ''])
        climb_rate = (climbs / mc) * 100
        
        strengths = []
        weaknesses = []
        
        if auto_scoring > 2: strengths.append("Excellent score en Auto")
        elif auto_scoring < 0.5: weaknesses.append("Auto faible ou inexistante")
        
        if teleop_scoring > 10: strengths.append("Gros tireur en Teleop")
        elif teleop_scoring < 3: weaknesses.append("Peu de balles en Teleop")
        
        if climb_rate > 70: strengths.append("Grimpe très fiable")
        elif climb_rate < 20: weaknesses.append("Grimpe rarement/échoue souvent")
        
        if accuracy > 4: strengths.append("Très précis aux tirs")
        elif accuracy < 2.5: weaknesses.append("Manque de précision")
        
        if intake_speed < 2.5: weaknesses.append("Intake lent/difficile")

        return {
            'team': team_num,
            'has_data': True,
            'auto_avg': round(auto_scoring, 1),
            'teleop_avg': round(teleop_scoring, 1),
            'climb_rate': round(climb_rate, 1),
            'strengths': strengths[:2],
            'weaknesses': weaknesses[:2],
            'drivetrain': pit.drivetrain_type if pit else 'Inconnu'
        }

    our_intel = [get_team_intel(t) for t in our_teams]
    opp_intel = [get_team_intel(t) for t in opp_teams]
    
    def rollup(intel_list):
        valid = [i for i in intel_list if i.get('has_data') and not i.get('pit_only')]
        if not valid: return {'auto': 0, 'teleop': 0, 'climb_avg': 0}
        return {
            'auto': round(sum(i['auto_avg'] for i in valid), 1),
            'teleop': round(sum(i['teleop_avg'] for i in valid), 1),
            'climb_avg': round(sum(i['climb_rate'] for i in valid) / len(valid), 1)
        }
        
    return jsonify({
        'match_key': match_key,
        'our_alliance': {
            'color': our_alliance_color,
            'teams': our_intel,
            'totals': rollup(our_intel)
        },
        'opp_alliance': {
            'color': 'blue' if our_alliance_color == 'red' else 'red',
            'teams': opp_intel,
            'totals': rollup(opp_intel)
        },
        'status': 'success'
    })
