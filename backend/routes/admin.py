from flask import Blueprint, request, jsonify, session
from models import db, User, MatchScoutData, Team

admin_bp = Blueprint('admin', __name__)


def check_admin():
    """Helper: verify current user is Admin or Head Scout."""
    if 'user_id' not in session:
        return None, jsonify({'error': 'Not logged in'}), 401
    user = User.query.get(session['user_id'])
    if not user or user.role not in ['Admin', 'Head Scout'] or not user.team_id:
        return None, jsonify({'error': 'Unauthorized'}), 403
    return user, None, None


@admin_bp.route('/api/team/join', methods=['POST'])
def join_team():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.json
    team_number = data.get('team_number')
    access_code = data.get('access_code')

    if not team_number or not access_code:
        return jsonify({'error': 'Missing team number or access code'}), 400

    team = Team.query.filter_by(team_number=int(team_number)).first()
    if not team:
        return jsonify({'error': 'Team not found in our system.'}), 404

    if team.access_code != access_code:
        return jsonify({'error': 'Invalid access code'}), 403

    user = User.query.get(session['user_id'])
    user.team_id = team.id
    user.status = 'pending'
    db.session.commit()

    return jsonify({'message': 'Join request submitted. Waiting for admin approval.'}), 200


@admin_bp.route('/api/admin/members', methods=['GET'])
def get_team_members():
    admin, err_resp, err_code = check_admin()
    if err_resp: return err_resp, err_code

    members = User.query.filter_by(team_id=admin.team_id).all()

    members_data = []
    for m in members:
        m_dict = m.to_dict()
        m_dict['matches_scouted'] = MatchScoutData.query.filter_by(scouter_id=m.id).count()
        members_data.append(m_dict)

    return jsonify(members_data), 200


@admin_bp.route('/api/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    admin, err_resp, err_code = check_admin()
    if err_resp: return err_resp, err_code

    user = User.query.get_or_404(user_id)
    if user.team_id != admin.team_id:
        return jsonify({'error': 'User not in your team'}), 403

    data = request.json
    action = data.get('action')  # 'approve' or 'reject'
    role = data.get('role', 'Stand Scout')

    if action == 'approve':
        user.status = 'active'
        user.role = role
    elif action == 'reject':
        user.team_id = None
        user.status = 'rejected'

    db.session.commit()
    return jsonify({'message': f'User {action}d successfully'}), 200


@admin_bp.route('/api/admin/role/<int:user_id>', methods=['POST'])
def change_role(user_id):
    admin, err_resp, err_code = check_admin()
    if err_resp: return err_resp, err_code

    user = User.query.get_or_404(user_id)
    if user.team_id != admin.team_id:
        return jsonify({'error': 'User not in your team'}), 403

    data = request.json
    new_role = data.get('role')
    if not new_role:
        return jsonify({'error': 'Missing role'}), 400

    user.role = new_role
    db.session.commit()
    return jsonify({'message': 'Role updated successfully'}), 200
