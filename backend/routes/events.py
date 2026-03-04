import secrets
import string
from flask import Blueprint, request, jsonify, abort
from models import db, Event, Team
import frc_api

events_bp = Blueprint('events', __name__)


@events_bp.route('/api/seasons', methods=['GET'])
def get_seasons():
    try:
        status = frc_api.get_status()
        max_season = status.get('max_season', 2026)
        valid_years = []
        for y in range(max_season, max_season - 6, -1):
            events = frc_api.get_events_for_year(y)
            if events:
                valid_years.append(y)
        return jsonify(valid_years), 200
    except Exception as e:
        abort(500, description=str(e))


@events_bp.route('/events', methods=['GET'])
def get_events():
    try:
        year_param = request.args.get('year')
        current_year = int(year_param) if year_param else 2024

        api_events = frc_api.get_events_for_year(current_year)

        if api_events:
            for api_event in api_events:
                existing_event = Event.query.filter_by(tba_key=api_event['key']).first()
                if not existing_event:
                    new_event = Event(
                        tba_key=api_event['key'],
                        name=api_event['name'],
                        location=api_event.get('city', 'Unknown') + ', ' + api_event.get('state_prov', ''),
                        date=api_event.get('start_date', 'Unknown'),
                        status='frc_api_synced'
                    )
                    db.session.add(new_event)
            db.session.commit()

        events = Event.query.filter(Event.tba_key.like(f"{current_year}%")).all()
        return jsonify([event.to_dict() for event in events]), 200
    except Exception as e:
        db.session.rollback()
        abort(500, description=str(e))


@events_bp.route('/events/<int:event_id>/teams', methods=['GET'])
def get_event_teams(event_id):
    try:
        event = Event.query.get_or_404(event_id, description="Event not found")

        if event.tba_key:
            api_teams = frc_api.get_teams_for_event(event.tba_key)
            if api_teams:
                for api_team in api_teams:
                    existing_team = Team.query.filter_by(team_number=api_team['team_number']).first()
                    if not existing_team:
                        existing_team = Team(
                            tba_key=api_team['key'],
                            team_number=api_team['team_number'],
                            team_name=api_team.get('name', f"Team {api_team['team_number']}"),
                            nickname=api_team.get('nickname', f"Team {api_team['team_number']}"),
                            access_code=f"{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))}{api_team['team_number']}"
                        )
                        db.session.add(existing_team)

                    if existing_team not in event.teams:
                        event.teams.append(existing_team)

                db.session.commit()

        return jsonify([team.to_dict() for team in event.teams]), 200
    except Exception as e:
        if "404 Not Found" in str(e):
            abort(404, description="Event not found")
        abort(500, description=str(e))
