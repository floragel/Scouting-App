import os, secrets, string, tempfile
from dotenv import load_dotenv
load_dotenv()
# import whisper  # Optional/unused dependency causing pyre lints
# from pydub import AudioSegment  # Optional/unused dependency causing pyre lints
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, abort, render_template_string
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, desc
from models import db, Event, Team, PitScoutData, MatchScoutData, User, ScoutAssignment
import frc_api
from frc_api import TBAHandler
import requests

# Initialize the Flask application
app = Flask(__name__)

# Lazy load whisper model
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        print("Loading Whisper model...")
        # Using base model for balance of speed and accuracy
        whisper_model = whisper.load_model("base")
    return whisper_model

@app.route('/api/voice-transcribe', methods=['POST'])
def voice_transcribe():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No audio file selected'}), 400

    # Save to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        temp_path = temp_audio.name

    try:
        # Load model and transcribe
        model = get_whisper_model()
        result = model.transcribe(temp_path)
        transcription = result.get('text', '').strip()

        return jsonify({'transcription': transcription})
    except Exception as e:
        print(f"Transcription error: {e}")
        return jsonify({'error': 'Failed to transcribe audio', 'details': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, '..', 'data', 'scouting.db')
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

# Ensure upload directory exists
os.makedirs(app.config['PITS_UPLOAD_FOLDER'], exist_ok=True)
app.config['STRATEGY_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'strategies')
os.makedirs(app.config['STRATEGY_UPLOAD_FOLDER'], exist_ok=True)

# Route to serve uploaded files
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route to serve unified shared assets (e.g. translation scripts)
@app.route('/shared_assets/<path:filename>')
def serve_shared_assets(filename):
    shared_dir = os.path.join(basedir, '..', 'frontend', 'shared')
    return send_from_directory(shared_dir, filename)

# ─── PWA Routes ───
# Service worker must be served from root '/' for proper scope
@app.route('/service-worker.js')
def serve_service_worker():
    return send_from_directory(os.path.join(basedir, 'static'), 'service-worker.js',
                               mimetype='application/javascript')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.path.join(basedir, 'static'), 'manifest.json',
                               mimetype='application/manifest+json')

@app.route('/offline')
def offline_page():
    template_path = os.path.join(basedir, '../frontend/pages/offline/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()

# Initialize the database with the app
db.init_app(app)

# ─── PWA & Mobile UI Injection Middleware ───
# Automatically inject PWA tags and Mobile UI assets into all HTML responses
PWA_HEAD_TAGS = '''
    <link rel="manifest" href="/manifest.json?v=4">
    <meta name="theme-color" content="#0d6cf2">
    <link rel="apple-touch-icon" href="/static/pwa/apple-touch-icon.png?v=4">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="FRC Scout">
    <link rel="stylesheet" href="/shared_assets/mobile.css?v=4">
'''
PWA_BODY_SCRIPT = '''
    <script src="/static/pwa-register.js?v=4" defer></script>
    <script src="/shared_assets/mobile-nav.js?v=4" defer></script>
'''

@app.after_request
def inject_mobile_and_pwa_assets(response):
    if response.content_type and 'text/html' in response.content_type:
        try:
            html = response.get_data(as_text=True)
            # Inject PWA/Mobile head tags before </head>
            if '</head>' in html and 'manifest' not in html:
                html = html.replace('</head>', PWA_HEAD_TAGS + '</head>', 1)
            # Inject PWA/Mobile scripts before </body>
            if '</body>' in html and 'pwa-register' not in html:
                html = html.replace('</body>', PWA_BODY_SCRIPT + '</body>', 1)
            response.set_data(html)
        except Exception:
            pass  # Don't break responses if injection fails
    return response

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
            
        # Handle password change
        if 'new_password' in data and data['new_password']:
            current_pass = data.get('current_password')
            if not current_pass or not check_password_hash(user.password_hash, current_pass):
                return jsonify({'error': 'Current password is incorrect'}), 400
            user.password_hash = generate_password_hash(data['new_password'])
            
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200

    return jsonify(user.to_dict()), 200

@app.route('/api/user/upload-profile-picture', methods=['POST'])
def upload_profile_picture():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    user = User.query.get(session['user_id'])
    
    if 'profile_picture' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['profile_picture']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        # Append user ID to ensure uniqueness
        filename = f"{user.id}_{filename}"
        upload_path = os.path.join(basedir, 'static', 'uploads', 'profiles')
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, filename))
        
        user.profile_picture = f"/static/uploads/profiles/{filename}"
        db.session.commit()
        
        return jsonify({'message': 'Profile picture uploaded successfully', 'url': user.profile_picture}), 200


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
    if not user or user.role not in ['Admin', 'Head Scout'] or not user.team_id:
        return None, jsonify({'error': 'Unauthorized'}), 403
    return user, None, None

@app.route('/api/admin/members', methods=['GET'])
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
            func.avg(MatchScoutData.auto_balls_scored).label('avg_auto'),
            func.avg(MatchScoutData.teleop_balls_shot).label('avg_teleop'),
            func.avg(MatchScoutData.teleop_intake_speed).label('avg_speed'),
            func.avg(MatchScoutData.teleop_shooter_accuracy).label('avg_accuracy')
        ).filter(MatchScoutData.team_id == team_id).first()

        team_dict = team.to_dict()
        
        # Location from TBA
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

        # Calculate Climb Rate
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

        # Normalize performance profile (0-100 scale for radar chart)
        # Max values for normalization: Auto: 10, Teleop: 20, Speed: 5, Accuracy: 5, Climb: 100%
        team_dict['performance_profile'] = {
            'auto': min(100, (match_stats.avg_auto or 0) / 10 * 100),
            'teleop': min(100, (match_stats.avg_teleop or 0) / 20 * 100),
            'speed': min(100, (match_stats.avg_speed or 0) / 5 * 100),
            'accuracy': min(100, (match_stats.avg_accuracy or 0) / 5 * 100),
            'climb': climb_rate
        }
        
        # Include pit data
        pit_data = PitScoutData.query.filter_by(team_id=team_id).first()
        if pit_data:
            team_dict['pit_info'] = pit_data.to_dict()

        # Match history
        matches = MatchScoutData.query.filter_by(team_id=team_id).order_by(desc(MatchScoutData.match_number)).all()
        team_dict['matches'] = []
        for m in matches:
            m_dict = m.to_dict()
            # Calculate total for summary
            m_dict['total_pts'] = (m.auto_balls_scored or 0) + (m.teleop_balls_shot or 0)
            team_dict['matches'].append(m_dict)

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

@app.route('/api/match-scout/upload-strategy', methods=['POST'])
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
        import base64
        import uuid
        
        # Remove data URI schema prefix if present
        if ',' in image_data_b64:
            image_data_b64 = image_data_b64.split(',')[1]
            
        img_bytes = base64.b64decode(image_data_b64)
        
        filename = f"strategy_match_{match_id}_{uuid.uuid4().hex[:6]}.png"
        filepath = os.path.join(app.config['STRATEGY_UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(img_bytes)
            
        match_data.strategy_image_url = f"/uploads/strategies/{filename}"
        db.session.commit()
        
        return jsonify({'message': 'Strategy saved successfully', 'url': match_data.strategy_image_url}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process strategy image: {str(e)}'}), 500

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
    return send_from_directory(os.path.join(basedir, '../frontend/pages/auth'), 'code.html')

@app.route('/register')
def register_page():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and not user.team_id:
            return redirect(url_for('onboarding_page'))
        return redirect(url_for('home'))
    return send_from_directory(os.path.join(basedir, '../frontend/pages/auth'), 'code.html')

@app.route('/onboarding')
def onboarding_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return send_from_directory(os.path.join(basedir, '../frontend/pages/onboarding'), 'code.html')

@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    template_path = os.path.join(basedir, '../frontend/pages/profile/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user)

@app.route('/admin-hub')
def admin_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    if not user or user.role not in ['Admin', 'Head Scout']:
        return redirect(url_for('scout_dashboard'))
    
    # 1. Fetch team members
    team_members = []
    if user.team_id:
        # Assuming team ID is available on user; else filter by team_access_code
        if hasattr(user, 'team_id') and user.team_id is not None:
            team_members = User.query.filter_by(team_id=user.team_id).all()
        else:
            team_members = User.query.filter_by(team_access_code=user.team_access_code).all()
            
    # Fallback if no team context exists yet
    if not team_members:
        team_members = User.query.all()
        
    members_data = []
    for m in team_members:
        m_dict = m.to_dict()
        m_dict['matches_scouted'] = MatchScoutData.query.filter_by(scouter_id=m.id).count()
        members_data.append(m_dict)
    
    # 2. Fetch Assignments
    assignments = ScoutAssignment.query.all() # Or filter by team if needed
    assignments_data = [a.to_dict() for a in assignments]
    
    # 3. Fetch Matches
    event_matches = []
    tba = TBAHandler()
    team_key = user.team.tba_key if user.team else 'frc6622'
    team_status = tba.get_team_status(team_key)
    if team_status and team_status.get('event_key'):
        em = frc_api.get_event_matches(team_status['event_key'])
        if em:
            valid_matches = [m for m in em if m.get('time')]
            valid_matches.sort(key=lambda x: x['time'])
            # Don't filter out past matches for admins, they might need to assign/re-assign them
            event_matches = valid_matches

    # The template already has access to event_matches natively, 
    # but the frontend JS needs a clean array without Jinja string corruption.
    # We will fetch this data via a separated endpoint below.
    import json
    template_path = os.path.join(basedir, '../frontend/pages/admin/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(), 
            user=user,
            team_members=members_data, 
            users_json=json.dumps(members_data),
            assignments=assignments_data, 
            assignments_json=json.dumps(assignments_data),
            event_matches=event_matches
        )

@app.route('/api/event/matches', methods=['GET'])
def get_event_matches_api():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    tba = TBAHandler()
    team_key = user.team.tba_key if user.team else 'frc6622'
    team_status = tba.get_team_status(team_key)
    
    if not team_status or not team_status.get('event_key'):
        return jsonify([])
        
    em = frc_api.get_event_matches(team_status['event_key'])
    if not em:
        return jsonify([])
        
    valid_matches = [m for m in em if m.get('time')]
    valid_matches.sort(key=lambda x: x['time'])
    
    all_count = len(valid_matches)
    
    if not request.args.get('show_all'):
        import time
        current_timestamp = int(time.time())
        upcoming = [m for m in valid_matches if m['time'] > current_timestamp]
        
        # If no upcoming matches, fall back to showing ALL matches
        # so the admin assignment dropdown is never empty
        if upcoming:
            valid_matches = upcoming
        # else: keep valid_matches as-is (all matches)
        
    return jsonify({
        'matches': valid_matches,
        'total': all_count,
        'filtered': len(valid_matches) < all_count
    })

@app.route('/api/team/next-matches', methods=['GET'])
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
    import time
    current_timestamp = int(time.time())
    
    # Filter matches where our team is playing
    team_matches = []
    for m in em:
        if not m.get('time'): continue
        all_teams = m['alliances']['red']['team_keys'] + m['alliances']['blue']['team_keys']
        if team_key in all_teams:
            m['our_alliance'] = 'red' if team_key in m['alliances']['red']['team_keys'] else 'blue'
            team_matches.append(m)
            
    # Sort and get future matches
    team_matches.sort(key=lambda x: x['time'])
    future_matches = [m for m in team_matches if m['time'] > (current_timestamp - 300)]
    
    return jsonify({
        'matches': future_matches[:3], # Return the next 3 matches
        'team_key': team_key
    })

@app.route('/api/team/regional-status', methods=['GET'])
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

    # Sort by end_date DESC, and prioritize higher event types (Championships)
    # Event types: 3 (CMP Division), 4 (CMP Finals), 2 (District CMP), 1 (District), 0 (Regional)
    def event_sort_key(e):
        return (e.get('end_date', ''), e.get('event_type', 0))

    events.sort(key=event_sort_key, reverse=True)

    selected_event = None
    rank = 'N/A'

    # Iterate through events to find the latest one that has a rank for this team
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

    # If no event with rank was found, default to the latest event info even if rank is N/A
    if not selected_event:
        selected_event = events[0]

    # Get win rate/record for the team in that year
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

@app.route('/api/user/next-assignment', methods=['GET'])
def get_next_assignment():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    user = User.query.get(session['user_id'])
    # Get the earliest pending assignment
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

@app.route('/api/admin/auto-assign', methods=['POST'])
def auto_assign():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(session['user_id'])
    if not user or user.role not in ['Admin', 'Head Scout']:
        return jsonify({'error': 'Unauthorized role'}), 403
        
    # Get all active scouts (Pit Scouts, Stand Scouts, Strategy Leads)
    team_members = []
    if hasattr(user, 'team_id') and user.team_id:
        team_members = User.query.filter_by(team_id=user.team_id).all()
        
    if not team_members:
        team_members = User.query.all()
        
    eligible_scouts = [m for m in team_members if m.role in ['Stand Scout', 'Pit Scout', 'Strategy Lead'] and m.status == 'active']
    
    if len(eligible_scouts) < 6:
        return jsonify({'error': f'Need at least 6 active scouts. Only found {len(eligible_scouts)}.'}), 400
        
    # Get upcoming matches
    tba = TBAHandler()
    team_key = user.team.tba_key if user.team else 'frc6622'
    team_status = tba.get_team_status(team_key)
    if not team_status or not team_status.get('event_key'):
        return jsonify({'error': 'Team not registered for an active event.'}), 400
        
    em = frc_api.get_event_matches(team_status['event_key'])
    import time
    current_time = int(time.time())
    
    # Normally we'd only want future matches but for testing/back-filling we'll just sort them
    upcoming_matches = [m for m in em if m.get('time')]
    
    # Sort backwards to prioritize the matches that are happening closest to now/next
    upcoming_matches.sort(key=lambda x: x['time'])
    
    # Filter out ones that are already fully assigned
    upcoming_matches = [m for m in upcoming_matches if ScoutAssignment.query.filter_by(match_key=m['key']).count() < 6]
    
    if not upcoming_matches:
        return jsonify({'error': 'No upcoming matches found to assign.'}), 400
        
    # We will assign the next 5 matches to keep the queue manageable
    matches_to_assign = upcoming_matches[:5]
    
    # Track scout fatigue (consecutive matches) and total assignments
    scout_stats = {
        s.id: {
            'total_assigned': ScoutAssignment.query.filter_by(user_id=s.id).count(),
            'consecutive': 0,
            'teams_scouted': set([d.team_key for d in ScoutAssignment.query.filter_by(user_id=s.id).all()])
        } for s in eligible_scouts
    }
    
    assignments_created = 0
    
    for match in matches_to_assign:
        # Check if match is already fully assigned (has 6 assignments)
        existing = ScoutAssignment.query.filter_by(match_key=match['key']).count()
        if existing >= 6:
            continue
            
        teams = match['alliances']['red']['team_keys'] + match['alliances']['blue']['team_keys']
        
        # Sort scouts by easiest workload first, penalizing consecutive matches
        # Score = total_assigned + (consecutive * 2)
        sorted_scouts = sorted(
            eligible_scouts, 
            key=lambda s: scout_stats[s.id]['total_assigned'] + (scout_stats[s.id]['consecutive'] * 2)
        )
        
        assigned_to_this_match = set()
        
        for team_key in teams:
            alliance_color = 'Red' if team_key in match['alliances']['red']['team_keys'] else 'Blue'
            
            # Check if this specific slot is already assigned
            if ScoutAssignment.query.filter_by(match_key=match['key'], team_key=team_key).first():
                continue
                
            # Find Best Scout (hasn't scouted this match yet, ideally hasn't scouted this team yet)
            best_scout = None
            for scout in sorted_scouts:
                if scout.id in assigned_to_this_match:
                    continue
                # Slight preference to NOT scout the same team twice
                if team_key in scout_stats[scout.id]['teams_scouted'] and len([s for s in sorted_scouts if s.id not in assigned_to_this_match]) > 1:
                    # If they've seen this team, check if next person hasn't
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
                
                # Update stats for next loop
                scout_stats[best_scout.id]['total_assigned'] += 1
                scout_stats[best_scout.id]['consecutive'] += 1
                scout_stats[best_scout.id]['teams_scouted'].add(team_key)
                assignments_created += 1
        
        # Reset consecutive counter for scouts who got a break this match
        for s in eligible_scouts:
            if s.id not in assigned_to_this_match:
                scout_stats[s.id]['consecutive'] = 0
                
    db.session.commit()
    return jsonify({
        'success': True, 
        'message': f'Successfully auto-assigned {assignments_created} scout slots across upcoming matches.'
    })

@app.route('/api/admin/assignments', methods=['POST'])
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

@app.route('/api/admin/assign-pit', methods=['POST'])
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

@app.route('/api/admin/auto-assign-pit', methods=['POST'])
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
            # Also check if already scouted
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

@app.route('/api/admin/assignments/all', methods=['DELETE'])
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

@app.route('/api/admin/assignments/<int:assignment_id>', methods=['DELETE'])
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

@app.route('/scout-dashboard')
def scout_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user = User.query.get(session['user_id'])
    is_admin = user.role in ['Admin', 'Head Scout']
    
    # 1. Fetch Assignments if not admin
    assignments = []
    matches_scouted = 0
    if not is_admin:
        assignment_type_filter = 'Pit' if user.role == 'Pit Scout' else 'Match'
        assign_records = ScoutAssignment.query.filter_by(user_id=user.id, status='Pending', assignment_type=assignment_type_filter).all()
        assignments = [a.to_dict() for a in assign_records]
        
        # Determine stats
        if user.role == 'Pit Scout':
            matches_scouted = PitScoutData.query.filter_by(scouter_id=user.id).count() if hasattr(PitScoutData, 'scouter_id') else 0
        else:
            matches_scouted = MatchScoutData.query.filter_by(scouter_id=user.id).count()
        
    # 2. Fetch Team Status using TBA API
    tba = TBAHandler()
    team_status = None
    if user.team and user.team.team_number:
        home_team_tba_key = f"frc{user.team.team_number}"
        team_status = tba.get_team_status(home_team_tba_key)
    
    # 3. Dynamic Performance Calculation
    if is_admin:
        # Admins scout nothing, but we could put general stats
        user_performance = {'matches_scouted': '-', 'accuracy': 'Admin'}
    else:
        accuracy = 'High' if matches_scouted > 20 else 'Medium' if matches_scouted > 5 else 'Low'
        user_performance = {'matches_scouted': matches_scouted, 'accuracy': accuracy}
        
    # 4. Event Schedule Calculation
    event_matches = []
    live_match = "TBD"
    dashboard_note = f"Welcome to the FRC Scouting App. Have a great event, {user.name.split()[0]}!"
    
    if team_status and team_status.get('event_key'):
        em = frc_api.get_event_matches(team_status['event_key'])
        if em:
            valid_matches = [m for m in em if m.get('time')]
            valid_matches.sort(key=lambda x: x['time'])
            
            import time
            current_unix = int(time.time())
            # Show only matches that haven't happened yet (minus a 10 min grace period so we don't hide the live one instantly)
            future_matches = [m for m in valid_matches if m['time'] > (current_unix - 600)]
            event_matches = future_matches
            
            if future_matches:
                live_m = future_matches[0]
                live_match = f"{live_m['comp_level'].upper()} {live_m['match_number']}"
            elif valid_matches:
                live_m = valid_matches[-1]
                live_match = f"{live_m['comp_level'].upper()} {live_m['match_number']} (Done)"

    
    # 5. Read template and render with Jinja
    is_pit_scout = user.role == 'Pit Scout'
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
        live_match=live_match
    )

@app.route('/profile/edit')
def profile_edit_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    template_path = os.path.join(basedir, '../frontend/pages/profile_edit/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user)

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user = User.query.get(session['user_id'])
    template_path = os.path.join(basedir, '../frontend/pages/events/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
        
    user = User.query.get(session['user_id'])
    template_path = os.path.join(basedir, '../frontend/pages/events/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user)

@app.route('/analytics')
def analytics():
    return redirect(url_for('head_scout_analytics_hub'))

@app.route('/match-scout/<int:assignment_id>')
def match_scout(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    user = User.query.get(session['user_id'])
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    
    # Optional: Verify the assignment belongs to the user, or user is admin
    if assignment.user_id != user.id and user.role != 'Admin':
        return "Not authorized to scout this match", 403
        
    template_path = os.path.join(basedir, '../frontend/pages/match_scout/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, assignment=assignment)

@app.route('/api/submit-match-scout', methods=['POST'])
def submit_match_scout():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    try:
        assignment_id = data.get('assignment_id')
        assignment = ScoutAssignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'error': 'Invalid assignment'}), 400
            
        # Get team ID and event ID based on the assignment keys
        team = Team.query.filter_by(team_number=int(assignment.team_key.replace('frc',''))).first()
        event = Event.query.filter_by(tba_key=assignment.match_key.split('_')[0]).first()
        
        if not team or not event:
            return jsonify({'error': 'Team or Event not found in local DB'}), 400
            
        match_num_str = assignment.match_key.split('_')[1]
        match_number = int(''.join(filter(str.isdigit, match_num_str))) # e.g. qm42 -> 42
        
        # Extract 2026 Fiche Scout data
        import json
        
        # safely parse starting position and trajectory, defaulting to stringified 'None' or empty array if missing.
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
            
        match_data = MatchScoutData(
            team_id=team.id,
            event_id=event.id,
            match_number=match_number,
            starting_position=starting_pos_str,
            auto_trajectory=auto_traj_str,
            auto_start_balls=int(data.get('auto_start_balls', 0)),
            auto_balls_shot=int(data.get('auto_balls_shot', 0)),
            auto_balls_scored=int(data.get('auto_balls_scored', 0)),
            auto_climb=data.get('auto_climb', 'None'),
            teleop_intake_speed=int(data.get('teleop_intake_speed', 3)),
            teleop_shooter_accuracy=int(data.get('teleop_shooter_accuracy', 3)),
            teleop_balls_shot=int(data.get('teleop_balls_shot', 0)),
            passes_bump=data.get('passes_bump') == True or data.get('passes_bump') == 'true',
            passes_trench=data.get('passes_trench') == True or data.get('passes_trench') == 'true',
            endgame_climb=data.get('endgame_climb', 'None'),
            notes=data.get('notes', ''),
            scouter_id=session['user_id']
        )
        
        db.session.add(match_data)
        
        # Once scouted, we can remove the assignment to clear their queue
        db.session.delete(assignment)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Match data saved', 'match_id': match_data.id})
    except Exception as e:
        print("Error saving match data:", e)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-pit-scout', methods=['POST'])
def submit_pit_scout():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.form
    assignment_id = data.get('assignment_id')
    team_key = data.get('team_key')
    team_name = data.get('team_name', '').strip()
    
    if not assignment_id or not team_key:
        return jsonify({'error': 'Missing required fields'}), 400
        
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    if assignment.user_id != session['user_id']:
        return jsonify({'error': 'Not your assignment'}), 403
        
    user = User.query.get(session['user_id'])
    event_id = None
    if user.team:
        event = user.team.events.first()
        if event:
            event_id = event.id
            
    if not event_id:
        tba = TBAHandler()
        status = None
        if user.team and user.team.team_number:
            status = tba.get_team_status(f"frc{user.team.team_number}")
        if status and status.get('event_key'):
            event_obj = Event.query.filter_by(tba_key=status['event_key']).first()
            if event_obj:
                event_id = event_obj.id

    team_number = int(team_key.replace('frc', ''))
    team = Team.query.filter_by(team_number=team_number).first()
    if not team:
        team = Team(tba_key=team_key, team_number=team_number, team_name=team_name or team_key)
        db.session.add(team)
        db.session.flush() # get team.id
    elif team_name and (not team.team_name or team.team_name == team.tba_key):
        team.team_name = team_name
    
    if not event_id:
        return jsonify({'error': 'Could not determine current event'}), 400

    try:
        pit_data = PitScoutData.query.filter_by(team_id=team.id, event_id=event_id).first()
        if not pit_data:
            pit_data = PitScoutData(team_id=team.id, event_id=event_id)
            db.session.add(pit_data)
            
        # Handle file upload
        photo_path = ''
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename != '':
                from werkzeug.utils import secure_filename
                import time
                filename = secure_filename(file.filename)
                unique_filename = f"t{team_key}_{int(time.time())}_{filename}"
                upload_path = os.path.join(basedir, 'static', 'uploads', 'pit_photos')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, unique_filename))
                photo_path = f"/static/uploads/pit_photos/{unique_filename}"
                
        # Update 2026 Rebuilt fields
        pit_data.drivetrain_type = data.get('drivetrain_type', 'Swerve')
        pit_data.weight = float(data.get('weight', 0) if data.get('weight') else 0)
        pit_data.motor_type = data.get('motor_type', 'Kraken X60')
        pit_data.motor_count = int(data.get('motor_count', 4) if data.get('motor_count') else 4)
        pit_data.dimensions_l = float(data.get('dim_l', 0) if data.get('dim_l') else 0)
        pit_data.dimensions_w = float(data.get('dim_w', 0) if data.get('dim_w') else 0)
        
        # 2026 Rebuilt Specifics
        pit_data.max_fuel_capacity = int(data.get('max_fuel', 50) if data.get('max_fuel') else 50)
        pit_data.climb_level = data.get('climb_level', 'None')
        pit_data.scoring_preference = data.get('scoring_pref', 'Both')
        pit_data.intake_type = data.get('intake_type', 'Both')

        # Autonomous Compliance
        pit_data.auto_leave = (data.get('auto_leave') == 'true')
        pit_data.auto_score_fuel = (data.get('auto_score_fuel') == 'true')
        pit_data.auto_collect_fuel = (data.get('auto_collect_fuel') == 'true')
        pit_data.auto_climb_l1 = (data.get('auto_climb_l1') == 'true')

        # Legacy fields
        pit_data.auto_pickup = (data.get('auto_pickup') == 'true')
        pit_data.notes = data.get('notes', '').strip()
        if photo_path:
            pit_data.photo_path = photo_path
        
        db.session.delete(assignment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Pit data saved'})
    except Exception as e:
        print("Error saving pit data:", e)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/pit-scout/<int:assignment_id>')
def pit_scout(assignment_id):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    if assignment.user_id != user.id:
        return "Unauthorized", 403
        
    template_path = os.path.join(basedir, '../frontend/pages/pit_scout/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, assignment=assignment)

@app.route('/head-scout-stats')
@app.route('/head-scout-analytics')
def head_scout_analytics_hub():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    # Allow both Admin and Head Scout roles
    if not user or user.role not in ['Head Scout', 'Admin']:
        return "Unauthorized: High-level analytics are reserved for Head Scouts and Admins.", 403
        
    # Get all pit data and match data
    pit_data = PitScoutData.query.all()
    match_data = MatchScoutData.query.all()
    
    # Get only events that have actual data (pit or match records)
    event_ids_with_data = set(p.event_id for p in pit_data) | set(m.event_id for m in match_data)
    events = Event.query.filter(Event.id.in_(event_ids_with_data)).all() if event_ids_with_data else []
    
    # Calculate Team Performance Averages
    import typing
    team_averages: typing.Dict[str, typing.Any] = {}
    
    # Mapping for string labels found in historical/imported data
    VAL_MAP = {
        'Very Slow': 1.0, 'Slow': 2.0, 'Medium': 3.0, 'Fast': 4.0, 'Very Fast': 5.0,
        'None': 0.0, 'N/A': 0.0
    }

    def to_num(val, default):
        if val is None: return float(default)
        if isinstance(val, (int, float)): return float(val)
        s = str(val).strip()
        if not s: return float(default)
        if s in VAL_MAP: return float(VAL_MAP[s])
        try: return float(s)
        except (ValueError, TypeError): return float(default)

    # Dictionary to store accuracy lists for SD calculation
    accuracy_lists = {}

    for m in match_data:
        t_num = m.team.team_number if (m.team and m.team.team_number) else (m.team_id if m.team_id else '?')
        t_id = f"frc{t_num}" if str(t_num).isdigit() else f"team_{t_num}"
        
        if t_id not in team_averages:
            team_averages[t_id] = {
                'team_number': t_num,
                'match_count': 0,
                'auto_balls_scored': 0.0,
                'teleop_balls_shot': 0.0,
                'teleop_intake_speed': 0.0,
                'teleop_shooter_accuracy': 0.0,
                'climb_count': 0,
                'l3_climb_count': 0,
                'matches': [] # List of match summaries
            }
            accuracy_lists[t_id] = []
        
        stats = team_averages[t_id]
        stats['match_count'] += 1
        
        acc = to_num(m.teleop_shooter_accuracy, 3.0)
        accuracy_lists[t_id].append(acc)
        
        stats['auto_balls_scored'] += to_num(m.auto_balls_scored, 0.0)
        stats['teleop_balls_shot'] += to_num(m.teleop_balls_shot, 0.0)
        stats['teleop_intake_speed'] += to_num(m.teleop_intake_speed, 3.0)
        stats['teleop_shooter_accuracy'] += acc
        
        stats['matches'].append({
            'number': m.match_number,
            'starting_position': m.starting_position,
            'auto': to_num(m.auto_balls_scored, 0),
            'tele': to_num(m.teleop_balls_shot, 0),
            'climb': m.endgame_climb or 'None',
            'strategy_url': m.strategy_image_url,
            'auto_trajectory': m.auto_trajectory
        })
        
        c_status = str(m.endgame_climb).strip() if m.endgame_climb else 'None'
        if c_status != 'None':
            stats['climb_count'] += 1
            if c_status == 'L3':
                stats['l3_climb_count'] += 1

    # Link Pit Data
    for p in pit_data:
        t_num = p.team.team_number if p.team else p.team_id
        t_id = f"frc{t_num}"
        if t_id in team_averages:
            team_averages[t_id]['pit'] = {
                'drivetrain': p.drivetrain_type,
                'motors': f"{p.motor_type} ({p.motor_count})",
                'weight': p.weight,
                'climb_level': p.climb_level,
                'photo_path': p.photo_path or ''
            }

    import math
    def calculate_sd(data):
        if len(data) < 2: return 0.0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / (len(data) - 1)
        return round(float(math.sqrt(float(variance))), 2)

    # Compute final averages
    for t_id, stats in team_averages.items():
        count = int(stats['match_count'])
        if count > 0:
            stats['auto_balls_avg'] = round(float(stats['auto_balls_scored']) / count, 2)
            stats['teleop_balls_avg'] = round(float(stats['teleop_balls_shot']) / count, 2)
            stats['intake_speed_avg'] = round(float(stats['teleop_intake_speed']) / count, 2)
            stats['accuracy_avg'] = round(float(stats['teleop_shooter_accuracy']) / count, 2)
            stats['accuracy_sd'] = calculate_sd(accuracy_lists[t_id])
            stats['climb_rate'] = round((float(stats['climb_count']) / count) * 100, 1)
            stats['l3_rate'] = round((float(stats['l3_climb_count']) / count) * 100, 1)
        else:
            stats['auto_balls_avg'] = 0.0
            stats['teleop_balls_avg'] = 0.0
            stats['intake_speed_avg'] = 0.0
            stats['accuracy_avg'] = 0.0
            stats['accuracy_sd'] = 0.0
            stats['climb_rate'] = 0.0
            stats['l3_rate'] = 0.0

    # We'll pass the data as JSON to the template for Chart.js
    import json
    template_path = os.path.join(basedir, '../frontend/pages/analytics/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(),
            user=user,
            events=events,
            pit_data_json=json.dumps([p.to_dict() for p in pit_data]),
            match_data_json=json.dumps([m.to_dict() for m in match_data]),
            team_averages_json=json.dumps(team_averages)
        )

# Route for Drag & Drop Pick List Generator
@app.route('/picklist')
def pick_list_hub():
    # Only allow Head Scouts and Admins
    user, err_resp, err_code = check_admin() # check_admin is actually head scout + admin
    if err_resp: return err_resp, err_code

    # Get all events (same as Head Scout hub)
    events = Event.query.all()

    # Re-use the Analytics Hub aggregation logic to get accurate data
    match_data = MatchScoutData.query.all()
    pit_data = PitScoutData.query.all()

    team_averages: Dict[str, Any] = {}
    accuracy_lists: Dict[str, list] = {}

    def to_num(val, default):
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    for m in match_data:
        t_id = f"frc{m.team_id}"
        if t_id not in team_averages:
            team_averages[t_id] = {
                'team_id': m.team_id, 'match_count': 0, 'auto_balls_scored': 0.0,
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

    # --- TBA FALLBACK ---
    # If no local match data exists, populate the list with all teams from
    # the user's current event via TBA, and use official TBA rankings if available.
    is_tba_fallback = False
    if not match_data:
        tba = TBAHandler()
        # Default to frc6622 if team not set
        team_key = user.team.tba_key if user.team else 'frc6622'
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
                    # Populate minimal stats
                    team_averages[tk] = {
                        'team_id': t_num, 'match_count': 0, 'auto_balls_scored': 0.0,
                        'teleop_balls_shot': 0.0, 'teleop_intake_speed': 0.0,
                        'teleop_shooter_accuracy': 0.0, 'climb_count': 0, 'l3_climb_count': 0,
                        'matches': [], 'pit': None,
                        'tba_rank': rankings_dict.get(tk, 999) # 999 if no rank
                    }

    # Link Pit Data (if any exists locally)
    for p in pit_data:
        t_id = f"frc{p.team_id}"
        if t_id in team_averages:
            team_averages[t_id]['pit'] = {
                'drivetrain': p.drivetrain_type,
                'motors': f"{p.motor_type} ({p.motor_count})"
            }

    import math
    def calculate_sd(data):
        if len(data) < 2: return 0.0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / (len(data) - 1)
        return round(float(math.sqrt(float(variance))), 2)

    # Compute final averages and Power Score
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

    # Sorting Logic: Official TBA Rank (ascending) if fallback, else Power Score (descending)
    if is_tba_fallback:
        sorted_teams.sort(key=lambda x: x.get('tba_rank', 999))
    else:
        sorted_teams.sort(key=lambda x: x.get('power_score', 0), reverse=True)

    import json
    template_path = os.path.join(basedir, '../frontend/pages/picklist/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(),
            user=user,
            sorted_teams_json=json.dumps(sorted_teams)
        )

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

    # Sorting Logic: Official TBA Rank (ascending) if fallback, else Power Score (descending)
    if is_tba_fallback:
        sorted_teams.sort(key=lambda x: x.get('tba_rank', 999))
    else:
        sorted_teams.sort(key=lambda x: x.get('power_score', 0), reverse=True)

    import json
    template_path = os.path.join(basedir, '../frontend/pages/picklist/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(),
            user=user,
            sorted_teams_json=json.dumps(sorted_teams)
        )

# --- Drive Team Briefing ---

@app.route('/drive-team-briefing')
def drive_team_briefing():
    """Serves the mobile-friendly Drive Team Briefing UI."""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    
    # Needs a list of active events to choose from
    pit_data = PitScoutData.query.all()
    match_data = MatchScoutData.query.all()
    event_ids_with_data = set(p.event_id for p in pit_data) | set(m.event_id for m in match_data)
    events = Event.query.filter(Event.id.in_(event_ids_with_data)).all() if event_ids_with_data else []
    
    import json
    template_path = os.path.join(basedir, '../frontend/pages/briefing/code.html')
    # If the file doesn't exist yet, we'll create it later
    if not os.path.exists(template_path):
        return "Frontend file not created yet", 404
        
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(
            f.read(),
            user=user,
            events=events
        )

@app.route('/api/team_matches/<int:event_id>')
def api_team_matches(event_id):
    """
    Fetches all matches for the home team at a specific event from TBA.
    Returns a sorted list of matches to populate a dropdown.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    event = Event.query.get_or_404(event_id)
    if not event.tba_key:
        return jsonify({'error': 'Event has no TBA key'}), 400
        
    # fetch matches from TBA
    matches = frc_api.get_event_matches(event.tba_key)
    if not matches:
        return jsonify([])
        
    user = User.query.get(session['user_id'])
    home_team_tba_key = f"frc{user.team.team_number}" if user.team and user.team.team_number else None
    
    team_matches = []
    for m in matches:
        # Check if home team is in this match
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
            
    # Sort by time, if time is None, fallback to 0
    team_matches.sort(key=lambda x: x['time'] if x['time'] is not None else 0)
    return jsonify(team_matches)

@app.route('/api/briefing/<int:event_id>/<match_key>')
def api_briefing(event_id, match_key):
    """
    Fetches TBA data for a specific match and computes strengths/weaknesses 
    for Notre Alliance vs Alliance Adverse based on our local DB.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    event = Event.query.get_or_404(event_id)
    if not event.tba_key:
        return jsonify({'error': 'Event has no TBA key'}), 400
        
    # 1. Fetch match from TBA
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
    
    # Determine our alliance
    if home_team in red_teams:
        our_alliance_color = 'red'
        our_teams = red_teams
        opp_teams = blue_teams
    elif home_team in blue_teams:
        our_alliance_color = 'blue'
        our_teams = blue_teams
        opp_teams = red_teams
    else:
        # If we are not playing in this match, default to Red vs Blue
        our_alliance_color = 'neutral'
        our_teams = red_teams
        opp_teams = blue_teams

    # 2. Compute intelligence for a team
    def get_team_intel(team_num):
        # Attempt to get local data for this event first, or overall if not enough
        matches = MatchScoutData.query.filter_by(event_id=event.id).join(Team).filter(Team.team_number == int(team_num)).all()
        # Fallback to all data if none for this event
        if not matches:
            matches = MatchScoutData.query.join(Team).filter(Team.team_number == int(team_num)).all()
            
        pit = PitScoutData.query.filter_by(event_id=event.id).join(Team).filter(Team.team_number == int(team_num)).first()
        if not pit:
            pit = PitScoutData.query.join(Team).filter(Team.team_number == int(team_num)).first()
            
        if not matches and not pit:
            return {'team': team_num, 'has_data': False}
            
        # Averages calculation (similar to analytics hub)
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
        
        # Determine strengths & weaknesses
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
            'strengths': strengths[:2], # max 2
            'weaknesses': weaknesses[:2], # max 2
            'drivetrain': pit.drivetrain_type if pit else 'Inconnu'
        }

    # 3. Compile report
    our_intel = [get_team_intel(t) for t in our_teams]
    opp_intel = [get_team_intel(t) for t in opp_teams]
    
    # Alliance Rollups
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

@app.route('/api/import/scout-data', methods=['POST'])
def import_scout_data():
    user, err_resp, err_code = check_admin()
    if err_resp: return err_resp, err_code
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
        
    file = request.files['file']
    if not file or not file.filename.endswith('.json'):
        return jsonify({'error': 'Invalid file type. Please upload a .json file.'}), 400
        
    try:
        import json
        data = json.load(file)
        
        # Determine if it's Pit or Match data based on metadata
        metadata = data.get('metadata', {})
        team_key = metadata.get('team_key')
        
        if not team_key:
            return jsonify({'error': 'Invalid JSON: Missing team_key in metadata'}), 400
            
        team = Team.query.filter_by(tba_key=team_key).first()
        if not team:
            # Try by team number
            team_number = int(team_key.replace('frc', ''))
            team = Team.query.filter_by(team_number=team_number).first()
            
        if not team:
            return jsonify({'error': f'Team {team_key} not found in database'}), 404

        # Assume current event if not specified
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

        # --- IMPORT LOGIC ---
        if 'technical_specs' in data: # It's Pit Data
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
            
        elif 'teleop' in data or 'match_metrics' in data: # It's Match Data
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
        db.session.rollback()
        print(f"Import error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/teams-dir')
def teams_dir():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    events = Event.query.order_by(desc(Event.date)).all()
    
    # Get live match info for header
    live_match = "Practice Match"
    if events:
        latest_event = events[0]
        try:
            from backend.frc_api import frc_api
            matches = frc_api.get_event_matches(latest_event.tba_key)
            if matches:
                 upcoming = [m for m in matches if m.get('actual_time') is None]
                 if upcoming:
                     live_match = f"Next: {upcoming[0].get('key').split('_')[-1].upper()}"
        except: pass

    template_path = os.path.join(basedir, '../frontend/pages/teams/code.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        return render_template_string(f.read(), user=user, events=events, live_match=live_match)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5002)
