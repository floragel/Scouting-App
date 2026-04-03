import os
import json
import requests
import time
from flask import Blueprint, session, redirect, url_for, send_from_directory, render_template_string, request, jsonify
from models import db, User, ScoutAssignment, MatchScoutData, PitScoutData, Event, Team
import frc_api
from frc_api import TBAHandler, BASE_URL, HEADERS
from .admin import check_admin

pages_bp = Blueprint('pages', __name__)
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
APP_VERSION = "2.0.26"

@pages_bp.route('/login')
def login_page():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and not user.team_id:
            return redirect(url_for('pages.onboarding_page'))
        return redirect(url_for('pages.home'))
    return send_from_directory(os.path.join(basedir, '../frontend/pages/auth'), 'code.html')

@pages_bp.route('/reset-password')
def reset_password_page():
    return send_from_directory(os.path.join(basedir, '../frontend/pages/auth'), 'code.html')

@pages_bp.route('/register')
def register_page():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and not user.team_id:
            return redirect(url_for('pages.onboarding_page'))
        return redirect(url_for('pages.home'))
    return send_from_directory(os.path.join(basedir, '../frontend/pages/auth'), 'code.html')

@pages_bp.route('/onboarding')
def onboarding_page():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    return send_from_directory(os.path.join(basedir, '../frontend/pages/onboarding'), 'code.html')

@pages_bp.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    user = User.query.get(session['user_id'])
    template_path = os.path.join(basedir, '../frontend/pages/profile/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, version=APP_VERSION)

@pages_bp.route('/admin-hub')
def admin_page():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('pages.scout_dashboard'))
    
    import datetime
    selected_year = request.args.get('year', 2026, type=int)
    
    # Get available seasons for the team or general
    tba = TBAHandler()
    team_key = user.team.tba_key if (user.team and user.team.tba_key) else (f"frc{user.team.team_number}" if user.team else 'frc6622')
    
    seasons = [2026, 2025, 2024] # Default simple list
    try:
        import requests
        from frc_api import BASE_URL, HEADERS
        y_res = requests.get(f"{BASE_URL}/team/{team_key}/years_participated", headers=HEADERS, timeout=5)
        if y_res.status_code == 200:
            seasons = sorted(y_res.json(), reverse=True)
    except: pass

    team_members = []
    if user.team_id:
        team_members = User.query.filter_by(team_id=user.team_id).all()
        
    if not team_members:
        team_members = User.query.all()
        
    members_data = []
    for m in team_members:
        m_dict = m.to_dict()
        m_dict['matches_scouted'] = MatchScoutData.query.filter_by(scouter_id=m.id).count()
        members_data.append(m_dict)
    
    assignments = ScoutAssignment.query.filter(ScoutAssignment.match_key.like(f"{selected_year}%")).all()
    assignments_data = [a.to_dict() for a in assignments]
    
    event_matches = []
    
    # Try to find matches for the selected year
    try:
        import requests
        from frc_api import BASE_URL, HEADERS
        # Find events for the team in the selected year
        e_res = requests.get(f"{BASE_URL}/team/{team_key}/events/{selected_year}/simple", headers=HEADERS, timeout=5)
        if e_res.status_code == 200 and e_res.json():
            events = sorted(e_res.json(), key=lambda x: x['end_date'], reverse=True)
            if events:
                # Find matches for the most recent event of that year
                for e in events:
                    em = frc_api.get_event_matches(e['key'])
                    if em:
                        valid_matches = [m for m in em if m.get('time')]
                        valid_matches.sort(key=lambda x: x['time'])
                        event_matches = valid_matches
                        if event_matches: break
    except Exception as e:
        print(f"Admin fallback error: {e}")

    # Final fallback: if no matches for selected year but it was 2026, try 2025 automatically?
    # No, let the user select it now that we have the selector.

    template_path = os.path.join(basedir, '../frontend/pages/admin/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(), 
            user=user,
            team_members=members_data, 
            users_json=json.dumps(members_data),
            assignments=assignments_data, 
            assignments_json=json.dumps(assignments_data),
            event_matches=event_matches,
            seasons=seasons,
            selected_year=selected_year,
            version=APP_VERSION
        )

@pages_bp.route('/scout-dashboard')
def scout_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    
    user = User.query.get(session['user_id'])
    is_admin = user.is_admin
    
    tba = TBAHandler()
    team_key = user.team.tba_key if (user.team and user.team.tba_key) else (f"frc{user.team.team_number}" if user.team else 'frc6622')
    seasons = [2026, 2025, 2024]
    try:
        import requests
        from frc_api import BASE_URL, HEADERS
        y_res = requests.get(f"{BASE_URL}/team/{team_key}/years_participated", headers=HEADERS, timeout=5)
        if y_res.status_code == 200:
            seasons = sorted(y_res.json(), reverse=True)
    except: pass
    
    selected_year = request.args.get('year', 2026, type=int)

    assignments = []
    matches_scouted = 0
    if not is_admin:
        assignment_type_filter = 'Pit' if user.has_role('Pit Scout') else 'Match'
        assign_records = ScoutAssignment.query.filter(
            ScoutAssignment.user_id == user.id,
            ScoutAssignment.status == 'Pending',
            ScoutAssignment.assignment_type == assignment_type_filter,
            ScoutAssignment.match_key.like(f"{selected_year}%")
        ).all()
        assignments = [a.to_dict() for a in assign_records]
        
        if user.has_role('Pit Scout'):
            matches_scouted = PitScoutData.query.filter_by(scouter_id=user.id).count() if hasattr(PitScoutData, 'scouter_id') else 0
        else:
            matches_scouted = MatchScoutData.query.filter_by(scouter_id=user.id).count()

    team_status = None
    if user.team and user.team.team_number:
        home_team_tba_key = f"frc{user.team.team_number}"
        team_status = tba.get_team_status(home_team_tba_key)
    
    if is_admin:
        user_performance = {'matches_scouted': '-', 'accuracy': 'Admin'}
    else:
        accuracy = 'High' if matches_scouted > 20 else 'Medium' if matches_scouted > 5 else 'Low'
        user_performance = {'matches_scouted': matches_scouted, 'accuracy': accuracy}
        
    event_matches = []
    live_match = "TBD"
    dashboard_note = f"Welcome to clear the field! Have a great event, {user.name.split()[0] if user.name else 'Scout'}!"
    
    try:
        import requests
        from frc_api import BASE_URL, HEADERS
        e_res = requests.get(f"{BASE_URL}/team/{team_key}/events/{selected_year}/simple", headers=HEADERS, timeout=5)
        if e_res.status_code == 200 and e_res.json():
            events = sorted(e_res.json(), key=lambda x: x['end_date'], reverse=True)
            if events:
                for e in events:
                    em = frc_api.get_event_matches(e['key'])
                    if em:
                        valid_matches = [m for m in em if m.get('time')]
                        valid_matches.sort(key=lambda x: x['time'])
                        # If viewing the current year, filter by time
                        if selected_year == 2026:
                            current_unix = int(time.time())
                            future_matches = [m for m in valid_matches if m['time'] > (current_unix - 600)]
                            event_matches = future_matches if future_matches else valid_matches
                        else:
                            event_matches = valid_matches
                        
                        if event_matches:
                            if selected_year == 2026:
                                live_m = event_matches[0]
                                live_match = f"{live_m.get('comp_level', '').upper()} {live_m.get('match_number', '')}"
                            else:
                                live_match = "Season Ended"
                        break
    except Exception as e:
        print(f"Error fetching scout dashboard matches: {e}")

    is_pit_scout = user.has_role('Pit Scout')
    template_name = 'dashboard_pit' if is_pit_scout else 'dashboard'
    template_path = os.path.join(basedir, f'../frontend/pages/{template_name}/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    return render_template_string(
        template_content, 
        is_admin=is_admin,
        assignments=assignments,
        team_status=team_status,
        user=user,
        user_performance=user_performance,
        dashboard_note=dashboard_note,
        event_matches=event_matches,
        live_match=live_match,
        seasons=seasons,
        selected_year=selected_year,
        version=APP_VERSION
    )

@pages_bp.route('/profile/edit')
def profile_edit_page():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    user = User.query.get(session['user_id'])
    template_path = os.path.join(basedir, '../frontend/pages/profile_edit/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, version=APP_VERSION)

@pages_bp.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    
    user = User.query.get(session['user_id'])
    template_path = os.path.join(basedir, '../frontend/pages/events/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, version=APP_VERSION)

@pages_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
        
    user = User.query.get(session['user_id'])
    template_path = os.path.join(basedir, '../frontend/pages/events/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, version=APP_VERSION)


@pages_bp.route('/match-scout/<int:assignment_id>')
def match_scout(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    
    user = User.query.get(session['user_id'])
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    
    if assignment.user_id != user.id and not user.is_admin:
        return "Not authorized to scout this match", 403
        
    template_path = os.path.join(basedir, '../frontend/pages/match_scout/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, assignment=assignment, version=APP_VERSION)

@pages_bp.route('/pit-scout/<int:assignment_id>')
def pit_scout(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    user = User.query.get(session['user_id'])
    
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    if assignment.user_id != user.id:
        return "Unauthorized", 403
        
    template_path = os.path.join(basedir, '../frontend/pages/pit_scout/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, assignment=assignment, version=APP_VERSION)

@pages_bp.route('/members')
def members_directory():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('pages.scout_dashboard'))
    
    team_members = []
    if user.team_id:
        team_members = User.query.filter_by(team_id=user.team_id).all()
    
    members_data = []
    for m in team_members:
        m_dict = m.to_dict()
        m_dict['matches_scouted'] = MatchScoutData.query.filter_by(scouter_id=m.id).count()
        members_data.append(m_dict)
        
    template_path = os.path.join(basedir, '../frontend/pages/members/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(), 
            user=user, 
            team_members=members_data,
            members_json=json.dumps(members_data),
            version=APP_VERSION
        )


@pages_bp.route('/picklist')
def pick_list_hub():
    user, err_resp, err_code = check_admin()
    if err_resp: return err_resp, err_code

    events = Event.query.all()
    match_data = MatchScoutData.query.all()
    pit_data = PitScoutData.query.all()

    import typing
    team_averages: typing.Dict[str, typing.Any] = {}
    accuracy_lists: typing.Dict[str, list] = {}

    def to_num(val, default):
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    for m in match_data:
        t_id = f"frc{m.team.team_number}" if (m.team and m.team.team_number) else f"frc{m.team_id}"
        if t_id not in team_averages:
            team_averages[t_id] = {
                'team_id': m.team_id, 'team_number': (m.team.team_number if m.team else m.team_id), 
                'match_count': 0, 'auto_balls_scored': 0.0,
                'teleop_balls_shot': 0.0, 'teleop_intake_speed': 0.0,
                'teleop_shooter_accuracy': 0.0, 'climb_count': 0, 'l3_climb_count': 0,
                'matches': [], 'pit': None
            }
            accuracy_lists[t_id] = []

        stats = team_averages[t_id]
        stats['match_count'] += 1
        
        acc = to_num(m.teleop_shooter_accuracy, 0.0)
        accuracy_lists[t_id].append(acc)
        
        stats['auto_balls_scored'] += to_num(m.auto_balls_scored, 0.0)
        stats['teleop_balls_shot'] += to_num(m.teleop_balls_shot, 0.0)
        stats['teleop_intake_speed'] += to_num(m.teleop_intake_speed, 3.0)
        stats['teleop_shooter_accuracy'] += acc
        
        c_status = str(m.endgame_climb).strip() if m.endgame_climb else 'None'
        if c_status != 'None':
            stats['climb_count'] += 1
            if c_status == 'L3':
                stats['l3_climb_count'] += 1

    is_tba_fallback = False
    if not match_data:
        tba = TBAHandler()
        team_key = user.team.tba_key if (user.team and user.team.tba_key) else (f"frc{user.team.team_number}" if user.team else 'frc6622')
        if not team_key: 
            team_key = 'frc6622'
            
        event_key = tba.get_team_latest_event(team_key)
        if event_key:
            event_teams = frc_api.get_teams_for_event(event_key)
            event_rankings = frc_api.get_event_rankings(event_key)
            
            rankings_dict = {}
            if event_rankings and 'rankings' in event_rankings:
                for rank_data in event_rankings['rankings']:
                    rankings_dict[rank_data['team_key']] = rank_data['rank']
                    
            if event_teams:
                is_tba_fallback = True
                for t in event_teams:
                    tk = t['key']
                    t_num = t['team_number']
                    team_averages[tk] = {
                        'team_id': t_num, 'team_number': t_num, 'match_count': 0, 'auto_balls_scored': 0.0,
                        'teleop_balls_shot': 0.0, 'teleop_intake_speed': 0.0,
                        'teleop_shooter_accuracy': 0.0, 'climb_count': 0, 'l3_climb_count': 0,
                        'matches': [], 'pit': None,
                        'tba_rank': rankings_dict.get(tk, 999)
                    }

    for p in pit_data:
        t_id = f"frc{p.team.team_number}" if (p.team and p.team.team_number) else f"frc{p.team_id}"
        if t_id in team_averages:
            team_averages[t_id]['pit'] = {
                'drivetrain': p.drivetrain_type,
                'motors': f"{p.motor_type} ({p.motor_count})"
            }

    sorted_teams = []
    for t_id, stats in team_averages.items():
        count = int(stats['match_count'])
        if count > 0:
            stats['auto_balls_avg'] = round(float(stats['auto_balls_scored']) / count, 2)
            stats['teleop_balls_avg'] = round(float(stats['teleop_balls_shot']) / count, 2)
            stats['accuracy_avg'] = round(float(stats['teleop_shooter_accuracy']) / count, 2)
            stats['climb_rate'] = round((float(stats['climb_count']) / count) * 100, 1)
            
            power_score = (stats['auto_balls_avg'] * 2) + (stats['teleop_balls_avg'] * (stats['accuracy_avg'] / 100)) + (stats['climb_rate'] / 20)
            stats['power_score'] = round(power_score, 2)
        else:
            stats['power_score'] = 0.0
        
        sorted_teams.append(stats)

    if is_tba_fallback:
        sorted_teams.sort(key=lambda x: x.get('tba_rank', 999))
    else:
        sorted_teams.sort(key=lambda x: x.get('power_score', 0), reverse=True)

    template_path = os.path.join(basedir, '../frontend/pages/picklist/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(),
            user=user,
            sorted_teams_json=json.dumps(sorted_teams),
            version=APP_VERSION
        )

@pages_bp.route('/drive-team-briefing')
def drive_team_briefing():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    user = User.query.get(session['user_id'])
    
    pit_data = PitScoutData.query.all()
    match_data = MatchScoutData.query.all()
    event_ids_with_data = set(p.event_id for p in pit_data) | set(m.event_id for m in match_data)
    events = Event.query.filter(Event.id.in_(event_ids_with_data)).all() if event_ids_with_data else []
    
    template_path = os.path.join(basedir, '../frontend/pages/briefing/code.html')
    if not os.path.exists(template_path):
        return "Frontend file not created yet", 404
        
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(),
            user=user,
            events=events,
            version=APP_VERSION
        )
