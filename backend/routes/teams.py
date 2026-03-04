import os
import time
import requests
from flask import Blueprint, request, jsonify, session, abort, redirect, url_for, render_template_string
from sqlalchemy import func, desc
from models import db, Event, Team, PitScoutData, MatchScoutData, User
import frc_api
from frc_api import TBAHandler

teams_bp = Blueprint('teams', __name__)

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


@teams_bp.route('/teams/<int:team_id>', methods=['GET'])
def get_team_details(team_id):
    try:
        team = Team.query.get_or_404(team_id, description="Team not found")

        match_stats = db.session.query(
            func.count(MatchScoutData.id).label('matches_played'),
            func.avg(MatchScoutData.auto_balls_scored).label('avg_auto'),
            func.avg(MatchScoutData.teleop_balls_shot).label('avg_teleop'),
            func.avg(MatchScoutData.teleop_intake_speed).label('avg_speed'),
            func.avg(MatchScoutData.teleop_shooter_accuracy).label('avg_accuracy')
        ).filter(MatchScoutData.team_id == team_id).first()

        team_dict = team.to_dict()

        if team.tba_key:
            try:
                tba_info = frc_api.get_team_info(team.tba_key)
                if tba_info:
                    city = tba_info.get('city', '')
                    state = tba_info.get('state_prov', '')
                    country = tba_info.get('country', '')
                    location_parts = [p for p in [city, state, country] if p]
                    team_dict['location'] = ", ".join(location_parts) if location_parts else "Location Unknown"
            except: pass

        climb_matches = MatchScoutData.query.filter(
            MatchScoutData.team_id == team_id,
            MatchScoutData.endgame_climb != 'None'
        ).count()
        total_matches = MatchScoutData.query.filter_by(team_id=team_id).count()
        climb_rate = (climb_matches / total_matches * 100) if total_matches > 0 else 0

        team_dict['stats'] = {
            'matches_played': match_stats.matches_played or 0,
            'avg_auto_points': round(match_stats.avg_auto or 0, 2),
            'avg_teleop_points': round(match_stats.avg_teleop or 0, 2),
            'avg_speed': round(match_stats.avg_speed or 0, 1),
            'avg_accuracy': round(match_stats.avg_accuracy or 0, 1),
            'climb_rate': round(climb_rate, 1)
        }

        team_dict['performance_profile'] = {
            'auto': min(100, (match_stats.avg_auto or 0) / 10 * 100),
            'teleop': min(100, (match_stats.avg_teleop or 0) / 20 * 100),
            'speed': min(100, (match_stats.avg_speed or 0) / 5 * 100),
            'accuracy': min(100, (match_stats.avg_accuracy or 0) / 5 * 100),
            'climb': climb_rate
        }

        pit_data = PitScoutData.query.filter_by(team_id=team_id).first()
        if pit_data:
            team_dict['pit_info'] = pit_data.to_dict()

        matches = MatchScoutData.query.filter_by(team_id=team_id).order_by(desc(MatchScoutData.match_number)).all()
        team_dict['matches'] = []
        for m in matches:
            m_dict = m.to_dict()
            m_dict['total_pts'] = (m.auto_balls_scored or 0) + (m.teleop_balls_shot or 0)
            team_dict['matches'].append(m_dict)

        return jsonify(team_dict), 200
    except Exception as e:
        if "404 Not Found" in str(e):
            abort(404, description="Team not found")
        abort(500, description=str(e))


@teams_bp.route('/api/team/next-matches', methods=['GET'])
def get_team_next_matches():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    team_key = user.team.tba_key if user.team else 'frc6622'

    tba = TBAHandler()
    team_status = tba.get_team_status(team_key)

    if not team_status or not team_status.get('event_key'):
        return jsonify([])

    em = frc_api.get_event_matches(team_status['event_key'])
    current_timestamp = int(time.time())

    team_matches = []
    for m in em:
        if not m.get('time'): continue
        all_teams = m['alliances']['red']['team_keys'] + m['alliances']['blue']['team_keys']
        if team_key in all_teams:
            m['our_alliance'] = 'red' if team_key in m['alliances']['red']['team_keys'] else 'blue'
            team_matches.append(m)

    team_matches.sort(key=lambda x: x['time'])
    future_matches = [m for m in team_matches if m['time'] > (current_timestamp - 300)]

    return jsonify({
        'matches': future_matches[:3],
        'team_key': team_key
    })


@teams_bp.route('/api/team/regional-status', methods=['GET'])
def get_team_regional_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])
    team_key = user.team.tba_key if user.team else 'frc6622'
    team_number = team_key.replace('frc', '')
    year = request.args.get('year', 2024)

    tba = TBAHandler()
    team_events_url = f"https://www.thebluealliance.com/api/v3/team/{team_key}/events/{year}/simple"
    res = requests.get(team_events_url, headers=tba.headers, timeout=5)

    if res.status_code != 200:
        return jsonify({'error': 'TBA Unavailable', 'rank': 'N/A', 'win_rate': '0%', 'event_name': 'Error'}), 200

    events = res.json()
    if not events:
        return jsonify({'error': 'No events found', 'rank': 'N/A', 'win_rate': '0%', 'event_name': 'No Event'}), 200

    def event_sort_key(e):
        return (e.get('end_date', ''), e.get('event_type', 0))

    events.sort(key=event_sort_key, reverse=True)

    selected_event = None
    rank = 'N/A'

    for e in events:
        event_key = e['key']
        rankings_url = f"https://www.thebluealliance.com/api/v3/event/{event_key}/rankings"
        rank_res = requests.get(rankings_url, headers=tba.headers, timeout=5)

        if rank_res.status_code == 200:
            rank_data = rank_res.json()
            if rank_data and 'rankings' in rank_data:
                for r in rank_data['rankings']:
                    if r.get('team_key') == team_key:
                        rank = f"#{r['rank']}"
                        selected_event = e
                        break

        if selected_event:
            break

    if not selected_event:
        selected_event = events[0]

    statbotics_url = f"https://api.statbotics.io/v3/team_year/{team_number}/{year}"
    sb_res = requests.get(statbotics_url, timeout=5)
    win_rate = "0%"
    if sb_res.status_code == 200:
        sb_data = sb_res.json()
        wr = sb_data.get('record', {}).get('winrate', 0)
        win_rate = f"{int(wr * 100)}%"

    return jsonify({
        'rank': rank,
        'win_rate': win_rate,
        'event_key': selected_event['key'],
        'event_name': selected_event['name']
    })


@teams_bp.route('/teams-dir')
def teams_dir():
    if 'user_id' not in session:
        return redirect(url_for('pages.login_page'))
    user = User.query.get(session['user_id'])
    events = Event.query.order_by(desc(Event.date)).all()

    live_match = "Practice Match"
    if events:
        latest_event = events[0]
        try:
            matches = frc_api.get_event_matches(latest_event.tba_key)
            if matches:
                upcoming = [m for m in matches if m.get('actual_time') is None]
                if upcoming:
                    live_match = f"Next: {upcoming[0].get('key').split('_')[-1].upper()}"
        except: pass

    template_path = os.path.join(basedir, '../frontend/pages/teams/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, events=events, live_match=live_match)
