from flask import Blueprint, request, jsonify, abort
from sqlalchemy import func, desc
from models import db, Team, MatchScoutData

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/headscout/rankings', methods=['GET'])
def get_rankings():
    try:
        total_points = func.avg(MatchScoutData.auto_points) + func.avg(MatchScoutData.teleop_points)
        rankings = db.session.query(
            Team.team_number,
            Team.nickname,
            func.avg(MatchScoutData.auto_points).label('avg_auto'),
            func.avg(MatchScoutData.teleop_points).label('avg_teleop'),
            total_points.label('avg_total_points')
        ).select_from(Team).join(MatchScoutData, Team.id == MatchScoutData.team_id).group_by(Team.id).order_by(
            desc('avg_total_points')
        ).all()
        
        result = []
        for rank, data in enumerate(rankings, 1):
             result.append({
                 'rank': rank,
                 'team_number': data.team_number,
                 'nickname': data.nickname,
                 'avg_auto': round(data.avg_auto or 0, 2) if data.avg_auto is not None else 0,
                 'avg_teleop': round(data.avg_teleop or 0, 2) if data.avg_teleop is not None else 0,
                 'avg_total_points': round(data.avg_total_points or 0, 2) if data.avg_total_points is not None else 0
             })
             
        return jsonify(result), 200

    except Exception as e:
        abort(500, description=str(e))

@analytics_bp.route('/api/headscout/match-report', methods=['GET'])
def get_match_report():
    try:
        teams_param = request.args.get('teams')
        if not teams_param:
            abort(400, description="Please provide a 'teams' query parameter (e.g., ?teams=1114,2056,254)")
            
        team_numbers = []
        try:
             team_numbers = [int(t.strip()) for t in teams_param.split(',')]
        except ValueError:
             abort(400, description="Team numbers must be integers separated by commas.")

        if len(team_numbers) > 6:
             abort(400, description="Please provide a maximum of 6 team numbers.")

        report = []
        for number in team_numbers:
             team = Team.query.filter_by(team_number=number).first()
             if not team:
                 report.append({
                     'team_number': number,
                     'error': 'Team not found in database'
                 })
                 continue
                 
             stats = db.session.query(
                 func.count(MatchScoutData.id).label('matches'),
                 func.avg(MatchScoutData.auto_points).label('avg_auto_points'),
                 func.avg(MatchScoutData.teleop_points).label('avg_teleop_points')
             ).filter(MatchScoutData.team_id == team.id).first()
             
             report.append({
                 'team_id': team.id,
                 'team_number': team.team_number,
                 'nickname': team.nickname,
                 'matches_played': stats.matches or 0,
                 'avg_auto_points': round(stats.avg_auto_points or 0, 2) if stats.avg_auto_points is not None else 0,
                 'avg_teleop_points': round(stats.teleop_points or 0, 2) if stats.teleop_points is not None else 0
             })
             
        return jsonify(report), 200

    except Exception as e:
        abort(500, description=str(e))
