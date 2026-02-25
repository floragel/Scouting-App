import os, secrets, string
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, abort, render_template_string
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, desc
from models import db, Event, Team, PitScoutData, MatchScoutData, User, ScoutAssignment
import frc_api
from frc_api import TBAHandler
# Initialize the Flask application
app = Flask(__name__)

# Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'scouting.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev_secret_key_scouting_app' # Change in production
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# File upload configuration
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PITS_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'pit_photos')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # 16 MB max upload size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
HOME_TEAM_NUMBER = 'frc6622' # Example, replace with actual home team number

# Ensure upload directory exists
os.makedirs(app.config['PITS_UPLOAD_FOLDER'], exist_ok=True)

# Route to serve uploaded files
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Initialize the database with the app
db.init_app(app)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Error Handlers
@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad Request', 'message': str(error.description)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found', 'message': str(error.description)}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method Not Allowed', 'message': str(error.description)}), 405

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred.'}), 500

# --- Auth Routes ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not all([email, password, name]):
        return jsonify({'error': 'Missing required fields'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    password_hash = generate_password_hash(password)
    user = User(email=email, password_hash=password_hash, name=name)
    db.session.add(user)
    db.session.commit()

    session.permanent = True
    session['user_id'] = user.id
    return jsonify({'message': 'Registered and logged in successfully.', 'user': user.to_dict()}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    session.permanent = True
    session['user_id'] = user.id
    return jsonify({'message': 'Logged in successfully', 'user': user.to_dict()}), 200

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/user/me', methods=['GET', 'PUT'])
def user_me():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    if request.method == 'PUT':
        data = request.json
        if 'name' in data:
            user.name = data['name']
        if 'email' in data:
            user.email = data['email']
            
        # Optional: handle password change if provided
        if 'password' in data and data['password']:
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(data['password'])
            
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200

    return jsonify(user.to_dict()), 200

# --- Team & Admin Routes ---
@app.route('/api/team/join', methods=['POST'])
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

def check_admin():
    if 'user_id' not in session:
        return None, jsonify({'error': 'Not logged in'}), 401
    user = User.query.get(session['user_id'])
    if not user or user.role != 'Admin' or not user.team_id:
        return None, jsonify({'error': 'Unauthorized'}), 403
    return user, None, None

@app.route('/api/admin/members', methods=['GET'])
def get_team_members():
    admin, err_resp, err_code = check_admin()
    if err_resp: return err_resp, err_code

    members = User.query.filter_by(team_id=admin.team_id).all()
    return jsonify([m.to_dict() for m in members]), 200

@app.route('/api/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    admin, err_resp, err_code = check_admin()
    if err_resp: return err_resp, err_code

    user = User.query.get_or_404(user_id)
    if user.team_id != admin.team_id:
        return jsonify({'error': 'User not in your team'}), 403

    data = request.json
    action = data.get('action') # 'approve' or 'reject'
    role = data.get('role', 'Stand Scout')

    if action == 'approve':
        user.status = 'active'
        user.role = role
    elif action == 'reject':
        user.team_id = None
        user.status = 'rejected'
    
    db.session.commit()
    return jsonify({'message': f'User {action}d successfully'}), 200

@app.route('/api/admin/role/<int:user_id>', methods=['POST'])
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

# --- Routes ---

# 0. GET /api/seasons: List available seasons from TBA that have events.
@app.route('/api/seasons', methods=['GET'])
def get_seasons():
    try:
        status = frc_api.get_status()
        max_season = status.get('max_season', 2026)
        valid_years = []
        # Check backend FRC API for last 6 years to see which have events
        for y in range(max_season, max_season - 6, -1):
            events = frc_api.get_events_for_year(y)
            if events:
                valid_years.append(y)
        return jsonify(valid_years), 200
    except Exception as e:
        abort(500, description=str(e))

# 1. GET /events: List all competitions (syncs with FRC API for the current year).
@app.route('/events', methods=['GET'])
def get_events():
    try:
        year_param = request.args.get('year')
        current_year = int(year_param) if year_param else 2024
        
        # 1. Fetch from TBA API
        api_events = frc_api.get_events_for_year(current_year)
        
        if api_events:
            # 2. Sync with local DB
            for api_event in api_events:
                # TBA uses string keys like '2024oncmp', our DB uses integer IDs.
                
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
            
        # 3. Return all events from local DB for the specified year
        events = Event.query.filter(Event.tba_key.like(f"{current_year}%")).all()
        return jsonify([event.to_dict() for event in events]), 200
    except Exception as e:
        db.session.rollback()
        abort(500, description=str(e))

# 2. GET /events/<id>/teams: List all teams at specific competition.
@app.route('/events/<int:event_id>/teams', methods=['GET'])
def get_event_teams(event_id):
    try:
        event = Event.query.get_or_404(event_id, description="Event not found")
        
        # Sync teams from TBA if we have a tba_key
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
                    
                    # Add to event representation if not already linked
                    if existing_team not in event.teams:
                        event.teams.append(existing_team)
                
                db.session.commit()
        
        # Return all teams synced to this event
        return jsonify([team.to_dict() for team in event.teams]), 200
    except Exception as e:
        if "404 Not Found" in str(e):
            abort(404, description="Event not found")
        abort(500, description=str(e))

# 3. GET /teams/<id>: Get full details of a team, including aggregated stats.
@app.route('/teams/<int:team_id>', methods=['GET'])
def get_team_details(team_id):
    try:
        team = Team.query.get_or_404(team_id, description="Team not found")
        
        # Aggregate match data
        match_stats = db.session.query(
            func.count(MatchScoutData.id).label('matches_played'),
            func.avg(MatchScoutData.auto_points).label('avg_auto_points'),
            func.avg(MatchScoutData.teleop_points).label('avg_teleop_points')
        ).filter(MatchScoutData.team_id == team_id).first()

        team_dict = team.to_dict()
        
        if team.tba_key:
            tba_info = frc_api.get_team_info(team.tba_key)
            if tba_info:
                city = tba_info.get('city', '')
                state = tba_info.get('state_prov', '')
                country = tba_info.get('country', '')
                location_parts = [p for p in [city, state, country] if p]
                team_dict['location'] = ", ".join(location_parts) if location_parts else "Location Unknown"
        team_dict['stats'] = {
            'matches_played': match_stats.matches_played or 0,
            'avg_auto_points': round(match_stats.avg_auto_points or 0, 2) if match_stats.avg_auto_points is not None else 0,
            'avg_teleop_points': round(match_stats.teleop_points or 0, 2) if match_stats.teleop_points is not None else 0
        }
        
        # Include pit data if available
        pit_data = PitScoutData.query.filter_by(team_id=team_id).first()
        if pit_data:
            team_dict['pit_info'] = pit_data.to_dict()

        # Include match history
        matches = MatchScoutData.query.filter_by(team_id=team_id).order_by(MatchScoutData.match_number).all()
        team_dict['matches'] = [match.to_dict() for match in matches]

        return jsonify(team_dict), 200
    except Exception as e:
        if "404 Not Found" in str(e):
            abort(404, description="Team not found")
        abort(500, description=str(e))

# 4. POST /submit/pit: Receive form data, save photo, store in SQLite.
@app.route('/submit/pit', methods=['POST'])
def submit_pit_data():
    try:
        # Get data from form (multipart/form-data)
        team_id = request.form.get('team_id')
        event_id = request.form.get('event_id')
        drivetrain_type = request.form.get('drivetrain_type')
        weight = request.form.get('weight')
        notes = request.form.get('notes')
        
        if not team_id or not event_id:
            abort(400, description="team_id and event_id are required fields")

        # Handle image upload
        photo_path = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Ensure unique filename
                unique_filename = f"t{team_id}_e{event_id}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                photo_path = os.path.join('uploads', 'pit_photos', unique_filename)
        
        # Create PitScoutData object
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
        # Handle unique constraint violation
        if "UNIQUE constraint failed" in str(e):
            abort(400, description="Pit scout data for this team at this event already exists.")
        abort(500, description=str(e))

# 5. POST /submit/match: Receive numerical data and save to SQLite.
@app.route('/submit/match', methods=['POST'])
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
            auto_points=data.get('auto_points', 0),
            auto_tasks=data.get('auto_tasks', 0),
            teleop_points=data.get('teleop_points', 0),
            teleop_tasks=data.get('teleop_tasks', 0),
            climb_status=data.get('climb_status'),
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

# 6. GET /api/headscout/rankings: Return ranked JSON list.
@app.route('/api/headscout/rankings', methods=['GET'])
def get_rankings():
    try:
        # Calculate sum of avg_auto + avg_teleop grouped by team
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

# 7. GET /api/headscout/match-report: Receive 6 team numbers, return comparison structure.
@app.route('/api/headscout/match-report', methods=['GET'])
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
                 
             # Get aggregated data
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

# --- Frontend Routes ---
# Serve the frontend HTML files natively through Flask

# --- Page Routes ---
@app.route('/login')
def login_page():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and not user.team_id:
            return redirect(url_for('onboarding_page'))
        return redirect(url_for('home'))
    return send_from_directory(os.path.join(basedir, '../user_login_&_registration_flow'), 'code.html')

@app.route('/register')
def register_page():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and not user.team_id:
            return redirect(url_for('onboarding_page'))
        return redirect(url_for('home'))
    return send_from_directory(os.path.join(basedir, '../user_login_&_registration_flow'), 'code.html')

@app.route('/onboarding')
def onboarding_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return send_from_directory(os.path.join(basedir, '../team_onboarding_&_access'), 'code.html')

@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return send_from_directory(os.path.join(basedir, '../user_profile_&_settings_hub'), 'code.html')

@app.route('/admin-hub')
def admin_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    # Only allow Admin/Head Scout to access the HTML page entirely
    if not user or user.role not in ['Admin', 'Head Scout']:
        return redirect(url_for('scout_dashboard'))
    return send_from_directory(os.path.join(basedir, '../admin_scout_management_hub'), 'code.html')

@app.route('/scout-dashboard')
def scout_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user = User.query.get(session['user_id'])
    is_admin = user.role in ['Admin', 'Head Scout']
    
    # 1. Fetch Assignments if not admin
    assignments = []
    if not is_admin:
        assign_records = ScoutAssignment.query.filter_by(user_id=user.id, status='Pending').all()
        assignments = [a.to_dict() for a in assign_records]
        
    # 2. Fetch Team Status using TBA API
    tba = TBAHandler()
    team_status = tba.get_team_status(HOME_TEAM_NUMBER)
    
    # 3. Read template and render with Jinja
    template_path = os.path.join(basedir, '../desktop_scout_dashboard_hub/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
        
    return render_template_string(
        template_content, 
        is_admin=is_admin,
        assignments=assignments,
        team_status=team_status,
        user=user
    )

@app.route('/profile/edit')
def profile_edit_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return send_from_directory(os.path.join(basedir, '../profile_&_settings_edit'), 'code.html')

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    # Default to the events dashboard
    return send_from_directory(os.path.join(basedir, '..', 'frc_events_&_dashboard'), 'code.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory(os.path.join(basedir, '..', 'frc_events_&_dashboard'), 'code.html')

@app.route('/analytics')
def analytics():
    return send_from_directory(os.path.join(basedir, '..', 'head_scout_analytics_hub'), 'code.html')

@app.route('/match-scout')
def match_scout():
    return send_from_directory(os.path.join(basedir, '..', 'match_scouting_entry'), 'code.html')

@app.route('/pit-scout')
def pit_scout():
    return send_from_directory(os.path.join(basedir, '..', 'pit_scouting_form'), 'code.html')

@app.route('/teams-dir')
def teams_dir():
    return send_from_directory(os.path.join(basedir, '..', 'teams_directory_&_profile'), 'code.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5002)
