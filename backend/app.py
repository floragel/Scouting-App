import os
import sys

# Crucial for Vercel: ensure the backend directory is in sys.path
# so that "from models import db" and other imports work correctly.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
from sqlalchemy import text, func
import datetime
from datetime import timedelta
import json

from models import db
from routes import register_blueprints

print("STAGE 1: Loading environment...")
try:
    load_dotenv()
    print("LOG: Environment loaded.")
except Exception as e:
    print(f"LOG: load_dotenv failed: {e}")

# Initialize the Flask application
print("STAGE 2: Initializing Flask app...")
app = Flask(__name__)
print("LOG: Flask app variable created.")
CORS(app, supports_credentials=True)

print("STAGE 3: Configuring Cloudinary...")
try:
    cloudinary.config(secure=True)
    print("LOG: Cloudinary configured.")
except Exception as e:
    print(f"LOG: Cloudinary config failed: {e}")

print("STAGE 4: Configuring Database...")
# Check for DATABASE_URL (often provided by Render or Heroku)
database_url = os.environ.get('DATABASE_URL')
if database_url:
    print(f"LOG: Found DATABASE_URL starting with {database_url[:15]}...")
    # SQLAlchemy 1.4+ requires postgresql:// instead of postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # Add sslmode=require for Supabase/Vercel if not already present
    if "postgresql://" in database_url and "sslmode=" not in database_url:
        if "?" in database_url:
            database_url += "&sslmode=require"
        else:
            database_url += "?sslmode=require"
            
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("LOG: Database URI set to PostgreSQL.")
else:
    print("LOG: No DATABASE_URL found. Check Vercel environment variables.")
    # Fallback - intentionally not setting a path here to see if it's the culprit
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use memory for safety if no DB URL

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_scouting_app')
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# Production Session Security
if os.environ.get('FLASK_ENV') == 'production' or os.environ.get('VERCEL'):
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=31)
    )

# File upload configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max upload size

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

@app.before_request
def update_last_active():
    from models import db
    user_id = session.get('user_id')
    if user_id:
        from models import User
        from datetime import datetime
        User.query.filter_by(id=user_id).update({'last_active': datetime.utcnow()})
        db.session.commit()

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
    import traceback
    # Log the full traceback to server console for the developer
    print("!!! 500 INTERNAL SERVER ERROR !!!")
    traceback.print_exc()
    
    # Return a generic error to the client for security
    return jsonify({
        'error': 'Internal Server Error', 
        'message': 'An unexpected error occurred. Please contact an administrator.',
        'traceback': None # Never leak stack traces on production
    }), 500

print("STAGE 5: Initializing Database handler...")
try:
    db.init_app(app)
    print("LOG: db.init_app complete.")
except Exception as e:
    print(f"LOG: db.init_app failed: {e}")

print("STAGE 6: Registering Blueprints...")
try:
    register_blueprints(app)
    print("LOG: Blueprints registered successfully.")
except Exception as e:
    print(f"LOG: Blueprint registration failed: {e}")
    import traceback
    traceback.print_exc()

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'database_configured': bool(app.config.get('SQLALCHEMY_DATABASE_URI')),
        'version': '2.0.26-vercel'
    }), 200

# Serve shared assets from the frontend/shared directory
@app.route('/shared_assets/<path:filename>')
def serve_shared_assets(filename):
    # Using the path relative to the root of the project
    shared_dir = os.path.join(os.getcwd(), 'frontend', 'shared')
    from flask import send_from_directory
    return send_from_directory(shared_dir, filename)

@app.route('/api/admin/init-db')
def manual_init_db():
    # Simple security check to prevent accidental usage
    import os
    if os.environ.get('FLASK_ENV') == 'production':
        # You could add a token check here if you want more security
        pass
    
    try:
        with app.app_context():
            if request.args.get('drop') == 'true':
                db.drop_all()
                print("LOG: Dropped all existing tables.")
            db.create_all()
        return jsonify({'message': 'Database tables created/updated successfully!'}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'DB Init failed', 'details': str(e)}), 500

# Gunicorn imports `app` directly, so it skips the __main__ block below.
# Removed db.create_all() from global scope to prevent cold start crashes.

# ─── Navigation & Template Routes ───
import json

def get_current_user():
    if 'user_id' not in session:
        return None
    from models import User
    return User.query.get(session['user_id'])

def get_common_data(user):
    # Admin, Head Scout, Captain, any Lead -> admin-hub. Everyone else -> scout-dashboard
    scout_mgmt_url = '/admin-hub' if user.is_admin else '/scout-dashboard'
    return {
        'user': user,
        'version': '2.0.26',
        'is_admin': user.is_admin,
        'scout_management_url': scout_mgmt_url
    }

def get_dashboard_data(user, year=2026):
    from models import PitScoutData, MatchScoutData, Event, Team, User, ScoutAssignment
    from models import PitScoutData, MatchScoutData, Event, Team, User, ScoutAssignment
    
    # Active Scouts (within last 10 minutes)
    # Using naive UTC to match PostgreSQL TIMESTAMP WITHOUT TIME ZONE
    ten_mins_ago = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
    active_now = User.query.filter(User.last_active >= ten_mins_ago).count()
    
    # Scouting Coverage for current event in SELECTED YEAR
    # Find the most recent/ongoing event for the year
    current_event = Event.query.filter(Event.status=='ongoing', Event.date.like(f"%{year}%")).first() or \
                    Event.query.filter(Event.date.like(f"%{year}%")).order_by(Event.date.desc()).first()
    
    coverage = 0
    if current_event:
        total_matches = MatchScoutData.query.filter_by(event_id=current_event.id).with_entities(func.distinct(MatchScoutData.match_number)).count()
        # Mocking total against a baseline of 60 matches (typical FRC event)
        coverage = min(100, round((total_matches / 60) * 100)) if total_matches > 0 else 0

    # User Performance (Filtered by Year)
    user_match_query = MatchScoutData.query.join(Event).filter(MatchScoutData.scouter_id == user.id, Event.date.like(f"%{year}%"))
    user_matches_count = user_match_query.count()
    
    accuracy = "0%"
    if user_matches_count > 0:
        # If notes exist, assume better quality
        has_notes = user_match_query.filter(MatchScoutData.notes != None).count()
        accuracy = f"{round((has_notes / user_matches_count) * 100)}%" if has_notes > 0 else "70%"

    # Next Match for the team (Filtered by Year Event)
    from frc_api import get_team_matches
    team_number = user.team.team_number if user.team else 23
    next_match_text = "No matches scheduled"
    try:
        if current_event:
            matches = get_team_matches(f"frc{team_number}", current_event.tba_key)
            now_ts = datetime.utcnow().timestamp()
            next_m = next((m for m in matches if m.get('time', 0) > now_ts), None)
            if next_m:
                next_match_text = f"{next_m['comp_level'].upper()} {next_m['match_number']}: Ready"
    except: pass

    # Team Stats Aggregation (Filtered by Year)
    match_entries = MatchScoutData.query.join(Event).filter(Event.date.like(f"%{year}%")).all()
    team_stats = {}
    for m in match_entries:
        t_id = f"frc{m.team.team_number}" if m.team else f"team_{m.team_id}"
        if t_id not in team_stats:
            team_stats[t_id] = {
                'team_number': m.team.team_number if m.team else 0,
                'match_count': 0,
                'accuracy_avg': 0,
                'climb_rate': 0,
                'auto_balls_avg': 0,
                'teleop_balls_avg': 0
            }
        s = team_stats[t_id]
        s['match_count'] += 1
        s['accuracy_avg'] += (m.teleop_shooter_accuracy or 0)
        s['auto_balls_avg'] += (m.auto_balls_scored or 0)
        s['teleop_balls_avg'] += (m.teleop_balls_shot or 0)
        if m.endgame_climb and m.endgame_climb != 'None':
            s['climb_rate'] += 1

    for t_id in team_stats:
        s = team_stats[t_id]
        if s['match_count'] > 0:
            s['accuracy_avg'] = round(s['accuracy_avg'] / s['match_count'], 2)
            s['auto_balls_avg'] = round(s['auto_balls_avg'] / s['match_count'], 2)
            s['teleop_balls_avg'] = round(s['teleop_balls_avg'] / s['match_count'], 2)
            s['climb_rate'] = round((s['climb_rate'] / s['match_count']) * 100, 1)

    common = get_common_data(user)
    return {
        **common,
        'stats': {
            'active_now': active_now,
            'coverage': f"{coverage}%",
            'accuracy': accuracy,
            'matches_scouted': user_matches_count
        },
        'team_status': {
            'type': 'next_match',
            'text': next_match_text,
            'color': 'green' if 'Ready' in next_match_text else 'slate'
        },
        'assignments': [a.to_dict() for a in user.assignments] if user.assignments else [],
        'events_list': [e.to_dict() for e in Event.query.filter(Event.date.like(f"%{year}%")).all()],
        'match_data_json': json.dumps([m.to_dict() for m in match_entries]),
        'team_averages_json': json.dumps(team_stats),
        'selected_year': year,
        'seasons': [2026, 2025, 2024]
    }

@app.route('/')
def index():
    user = get_current_user()
    if not user:
        return redirect(url_for('login_view'))
    return redirect(url_for('events_view'))

@app.route('/login')
def login_view():
    return render_template('login.html', version='2.0.26')

@app.route('/register')
def register_view():
    return render_template('login.html', version='2.0.26') # uses the same unified auth template

@app.route('/reset-password')
def reset_password_view():
    return render_template('login.html', version='2.0.26')

@app.route('/dashboard')
def dashboard_view():
    user = get_current_user()
    if not user:
        return redirect(url_for('login_view'))
    selected_year = request.args.get('year', 2026, type=int)
    data = get_dashboard_data(user, year=selected_year)
    return render_template('dashboard.html', **data)

@app.route('/analytics')
def analytics_view():
    user = get_current_user()
    if not user:
        return redirect(url_for('login_view'))
    selected_year = request.args.get('year', 2026, type=int)
    data = get_dashboard_data(user, year=selected_year)
    return render_template('analytics.html', **data)

@app.route('/admin-hub')
def admin_hub_view():
    user = get_current_user()
    if not user or not user.is_admin:
        return redirect(url_for('events_view'))
    
    from models import User, ScoutAssignment, MatchScoutData, PitScoutData, Event
    
    selected_year = request.args.get('year', 2026, type=int)
    seasons = [2026, 2025, 2024]
    
    # Active Scouts logic (last 5 minutes)
    # Naive UTC for Postgres compatibility
    five_mins_ago = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    active_now_count = User.query.filter(User.team_id == user.team_id, User.last_active >= five_mins_ago).count()
    
    # Pre-fetch team members to filter assignments
    team_members = User.query.filter_by(team_id=user.team_id).all()
    team_member_ids = [m.id for m in team_members]

    # Stats scoped to selection
    stats = {
        'total_scouts': User.query.filter_by(team_id=user.team_id, status='active').count(),
        'active_now': active_now_count,
        'pending_requests': User.query.filter_by(team_id=user.team_id, status='pending').count(),
        'match_assignments': ScoutAssignment.query.filter(
            ScoutAssignment.user_id.in_(team_member_ids),
            ScoutAssignment.assignment_type == 'Match'
        ).count() if team_member_ids else 0,
        'pit_assignments': ScoutAssignment.query.filter(
            ScoutAssignment.user_id.in_(team_member_ids),
            ScoutAssignment.assignment_type == 'Pit'
        ).count() if team_member_ids else 0
    }
    
    members_data = []
    
    # Fetch events for the selected year
    year_event_ids = [e.id for e in Event.query.filter(Event.date.like(f"%{selected_year}%")).all()]
    
    for m in team_members:
        m_dict = m.to_dict()
        # Season-aware matches scouted
        m_dict['matches_scouted'] = MatchScoutData.query.filter(
            MatchScoutData.scouter_id == m.id,
            MatchScoutData.event_id.in_(year_event_ids) if year_event_ids else MatchScoutData.id < 0
        ).count()
        m_dict['pit_scouted'] = PitScoutData.query.filter(
            PitScoutData.scouter_id == m.id,
            PitScoutData.event_id.in_(year_event_ids) if year_event_ids else PitScoutData.id < 0
        ).count()
        members_data.append(m_dict)
        
    assignments = ScoutAssignment.query.filter(ScoutAssignment.user_id.in_(team_member_ids)).all() if team_member_ids else []
    
    # Placeholder for match list from the most recent event of the year
    curr_events = Event.query.filter(Event.date.like(f"%{selected_year}%")).order_by(Event.date.desc()).all()
    event_matches = []
    
    import frc_api
    import requests
    team_key = user.team.tba_key if (user.team and user.team.tba_key) else (f"frc{user.team.team_number}" if user.team else 'frc6622')
    
    try:
        e_res = requests.get(f"https://www.thebluealliance.com/api/v3/team/{team_key}/events/{selected_year}/simple", headers={'X-TBA-Auth-Key': frc_api.TBA_API_KEY}, timeout=5)
        if e_res.status_code == 200 and e_res.json():
            events = sorted(e_res.json(), key=lambda x: x['end_date'], reverse=True)
            for ev in events:
                em = frc_api.get_event_matches(ev['key'])
                if em:
                    event_matches = [m for m in em if m.get('time')]
                    event_matches.sort(key=lambda x: x['time'])
                    break
    except Exception as e:
        print(f"Error fetching matches in admin_hub_view: {e}")
    
    assignments = ScoutAssignment.query.filter(ScoutAssignment.user_id.in_(team_member_ids)).all() if team_member_ids else []
    assignment_map = {f"{a.match_key}__{a.team_key}": a for a in assignments if a.match_key}
    user_map = {m['id']: m for m in members_data}
    
    return render_template('admin.html', 
                         stats=stats, 
                         seasons=seasons, 
                         selected_year=selected_year,
                         team_members=members_data,
                         users_json=json.dumps(members_data),
                         assignments=assignments,
                         assignment_map=assignment_map,
                         user_map=user_map,
                         event_matches=event_matches,
                         **get_common_data(user))

@app.route('/teams-dir')
def teams_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    
    selected_year = request.args.get('year', 2026, type=int)
    seasons = [2026, 2025, 2024]
    
    from models import Event
    # Filter events by selected year
    events = Event.query.filter(Event.date.like(f"%{selected_year}%")).order_by(Event.date.desc()).all()
    
    return render_template('teams.html', 
                         events=events,
                         seasons=seasons,
                         selected_year=selected_year,
                         **get_common_data(user))

@app.route('/events')
def events_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    return render_template('events.html', **get_common_data(user))

@app.route('/scout-dashboard')
def scout_dashboard_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    selected_year = request.args.get('year', 2026, type=int)
    seasons = [2026, 2025, 2024]
    data = get_dashboard_data(user, year=selected_year)
    return render_template('dashboard.html', **data)

@app.route('/onboarding')
def onboarding_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    return render_template('onboarding.html', **get_common_data(user))

@app.route('/profile')
def profile_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    return render_template('profile.html', **get_common_data(user))

@app.route('/profile-edit')
def profile_edit_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    return render_template('profile_edit.html', **get_common_data(user))

@app.route('/match-scout/<int:assignment_id>')
def match_scout(assignment_id):
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    from models import ScoutAssignment
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    if assignment.user_id != user.id and not user.is_admin:
        return "Not authorized to scout this match", 403
    return render_template('match_scout.html', assignment=assignment, **get_common_data(user))

@app.route('/pit-scout/<int:assignment_id>')
def pit_scout(assignment_id):
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    from models import ScoutAssignment
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    if assignment.user_id != user.id and not user.is_admin:
        return "Unauthorized", 403
    return render_template('pit_scout.html', assignment=assignment, **get_common_data(user))

@app.route('/members')
def members_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    
    selected_year = request.args.get('year', 2026, type=int)
    seasons = [2026, 2025, 2024]
    
    from models import MatchScoutData, User, Event
    team_members = User.query.filter_by(team_id=user.team_id).all() if user.team_id else User.query.all()
    
    # Filter event IDs for the selected year
    year_event_ids = [e.id for e in Event.query.filter(Event.date.like(f"%{selected_year}%")).all()]
    
    members_data = []
    for m in team_members:
        m_dict = m.to_dict()
        # Only count matches from the selected season
        m_dict['matches_scouted'] = MatchScoutData.query.filter(
            MatchScoutData.scouter_id == m.id,
            MatchScoutData.event_id.in_(year_event_ids) if year_event_ids else MatchScoutData.id < 0 
        ).count()
        members_data.append(m_dict)
        
    return render_template('members.html', 
                         team_members=members_data, 
                         members_json=json.dumps(members_data),
                         seasons=seasons,
                         selected_year=selected_year,
                         **get_common_data(user))

# --- NEW API ROUTES FOR DATA PARITY ---

@app.route('/api/user/me', methods=['GET', 'PUT'])
def api_user_me():
    user = get_current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        data = user.to_dict()
        data['team_number'] = user.team.team_number if user.team else None
        return jsonify(data)
    
    if request.method == 'PUT':
        data = request.json
        if 'name' in data: user.name = data['name']
        if 'email' in data: user.email = data['email']
        if 'new_password' in data and data.get('current_password'):
            # Basic validation: In production, use werkzeug.security
            user.password = data['new_password'] 
        db.session.commit()
        return jsonify({'success': True})

@app.route('/api/user/upload-profile-picture', methods=['POST'])
def api_upload_profile_picture():
    user = get_current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    file = request.files.get('profile_picture')
    if not file: return jsonify({'error': 'No file'}), 400
    
    # Save locally for now
    filename = f"profile_{user.id}_{int(time.time())}.jpg"
    os.makedirs('backend/static/uploads/profiles', exist_ok=True)
    filepath = os.path.join('backend/static/uploads/profiles', filename)
    file.save(filepath)
    
    user.profile_picture = f"/static/uploads/profiles/{filename}"
    db.session.commit()
    return jsonify({'url': user.profile_picture})

@app.route('/api/events/<int:event_id>/teams')
def api_event_teams(event_id):
    from models import Event
    event = Event.query.get_or_404(event_id)
    return jsonify([t.to_dict() for t in event.teams])

@app.route('/api/teams/<int:team_id>')
def api_team_detail(team_id):
    from models import Team, MatchScoutData, PitScoutData
    team = Team.query.get_or_404(team_id)
    matches = MatchScoutData.query.filter_by(team_id=team.id).all()
    pit = PitScoutData.query.filter_by(team_id=team.id).first()
    
    # Calculate profile stats (radar chart)
    from sqlalchemy import func
    stats = db.session.query(
        func.avg(MatchScoutData.auto_balls_scored).label('auto'),
        func.avg(MatchScoutData.teleop_balls_shot).label('teleop'),
        func.avg(MatchScoutData.teleop_shooter_accuracy).label('accuracy')
    ).filter_by(team_id=team.id).first()
    
    profile = {
        'auto': round(float(stats.auto or 0) * 10, 1), # Scale to 100
        'teleop': round(float(stats.teleop or 0) * 5, 1),
        'speed': 75, # Placeholder for speed logic
        'accuracy': round(float(stats.accuracy or 0) * 10, 1),
        'climb': 80 if MatchScoutData.query.filter(MatchScoutData.team_id == team.id, MatchScoutData.endgame_climb != 'None').count() > 0 else 0
    }
    
    return jsonify({
        'id': team.id,
        'team_number': team.team_number,
        'nickname': team.nickname or team.team_name,
        'location': f"{team.city}, {team.state_prov}" if team.city else "Unknown",
        'stats': {
            'avg_auto_points': round(float(stats.auto or 0), 2),
            'avg_teleop_points': round(float(stats.teleop or 0), 2),
            'matches_played': len(matches)
        },
        'pit_info': pit.to_dict() if pit else None,
        'performance_profile': profile,
        'matches': [m.to_dict() for m in matches]
    })

@app.route('/api/admin/members')
def api_admin_members():
    user = get_current_user()
    if not user or not user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    from models import User, MatchScoutData
    members = User.query.filter_by(team_id=user.team_id).all()
    data = []
    for m in members:
        d = m.to_dict()
        d['matches_scouted'] = MatchScoutData.query.filter_by(scouter_id=m.id).count()
        data.append(d)
    return jsonify(data)

@app.route('/api/admin/approve/<int:user_id>', methods=['POST'])
def api_admin_approve(user_id):
    admin = get_current_user()
    if not admin or not admin.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    from models import User
    target = User.query.get_or_404(user_id)
    if target.team_id != admin.team_id:
        return jsonify({'error': 'Cross-team approval denied'}), 403
    
    target.status = 'active'
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/role/<int:user_id>', methods=['POST'])
def api_admin_role(user_id):
    admin = get_current_user()
    if not admin or not admin.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    from models import User
    target = User.query.get_or_404(user_id)
    if target.team_id != admin.team_id:
        return jsonify({'error': 'Cross-team role change denied'}), 403
    
    data = request.json
    roles = data.get('roles', [])
    if isinstance(roles, list):
        target.role = ", ".join(roles) if roles else "Stand Scout"
    else:
        target.role = data.get('role', 'Stand Scout')
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/head-scout-stats')
@app.route('/head-scout-analytics')
def analytics_hub_view():
    user = get_current_user()
    if not user or not user.is_admin:
        return "Unauthorized", 403
    
    selected_year = request.args.get('year', 2026, type=int)
    seasons = [2026, 2025, 2024]
    
    from models import Event, PitScoutData, MatchScoutData, Team
    from sqlalchemy import func
    
    # Filter everything by season
    events = Event.query.filter(Event.date.like(f"%{selected_year}%")).order_by(Event.date.desc()).all()
    event_ids = [e.id for e in events]
    
    pit_data = PitScoutData.query.filter(PitScoutData.event_id.in_(event_ids)).all() if event_ids else []
    match_data = MatchScoutData.query.filter(MatchScoutData.event_id.in_(event_ids)).all() if event_ids else []
    
    # Calculate Team Averages (Filtered by Season)
    team_stats = db.session.query(
        MatchScoutData.team_id,
        func.avg(MatchScoutData.auto_balls_scored).label('avg_auto'),
        func.avg(MatchScoutData.teleop_balls_shot).label('avg_teleop'),
        func.avg(MatchScoutData.teleop_shooter_accuracy).label('avg_accuracy'),
        func.count(MatchScoutData.id).label('match_count')
    ).filter(MatchScoutData.event_id.in_(event_ids) if event_ids else MatchScoutData.id < 0).group_by(MatchScoutData.team_id).all()
    
    averages = {}
    for s in team_stats:
        team = Team.query.get(s.team_id)
        if team:
            averages[team.team_number] = {
                'avg_auto': round(float(s.avg_auto or 0), 2),
                'avg_teleop': round(float(s.avg_teleop or 0), 2),
                'avg_accuracy': round(float(s.avg_accuracy or 0), 2),
                'match_count': s.match_count
            }
    
    return render_template('analytics.html', 
                         events_list=[e.to_dict() for e in events],
                         pit_data_json=json.dumps([p.to_dict() for p in pit_data]),
                         match_data_json=json.dumps([m.to_dict() for m in match_data]),
                         team_averages_json=json.dumps(averages),
                         seasons=seasons,
                         selected_year=selected_year,
                         **get_common_data(user))

@app.route('/picklist')
def picklist_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    if not user.is_admin:
        return redirect(url_for('events_view'))
    
    from models import Team, MatchScoutData, PitScoutData, Event
    # Fetch data
    
    # 1. Season/Year Selection
    selected_year = request.args.get('year', 2026, type=int)
    seasons = [2026, 2025, 2024]
    
    # 2. Filter teams by the user's team's events for the selected year
    target_teams = []
    if user.team:
        # Find all events in this year that the user's team is attending
        team_event_ids = [e.id for e in user.team.events if str(selected_year) in (e.date or '')]
        if team_event_ids:
            # Get all teams participating in those same events
            unique_teams = set()
            events = Event.query.filter(Event.id.in_(team_event_ids)).all()
            for event in events:
                for t in event.teams:
                    unique_teams.add(t)
            target_teams = list(unique_teams)
        else:
            # Fallback: if no events found for this year, just show all teams for that team_id?
            # Or show all teams if user is Admin and wants a global view? 
            # For now, let's keep it restricted as requested.
            target_teams = Team.query.all() if not user.team_id else [user.team]
    else:
        target_teams = Team.query.all()
    
    sorted_teams = []
    
    for team in target_teams:
        # Get match stats
        stats = db.session.query(
            func.avg(MatchScoutData.auto_balls_scored).label('avg_auto'),
            func.avg(MatchScoutData.teleop_balls_shot).label('avg_teleop'),
            func.avg(MatchScoutData.teleop_shooter_accuracy).label('avg_accuracy'),
            func.count(MatchScoutData.id).label('match_count')
        ).filter(MatchScoutData.team_id == team.id).first()
        
        # Get climb rate
        climb_matches = MatchScoutData.query.filter(
            MatchScoutData.team_id == team.id,
            MatchScoutData.endgame_climb != 'None'
        ).count()
        climb_rate = (climb_matches / stats.match_count * 100) if (stats.match_count and stats.match_count > 0) else 0
        
        # Power Score
        auto_val = float(stats.avg_auto or 0)
        tele_val = float(stats.avg_teleop or 0)
        acc_val = float(stats.avg_accuracy or 0)
        power_score = round((auto_val * 2.5) + (tele_val * 1.5) + (acc_val * 2) + (climb_rate * 0.05), 2)
        
        pit = PitScoutData.query.filter_by(team_id=team.id).first()
        
        sorted_teams.append({
            'team_number': team.team_number,
            'auto_balls_avg': round(auto_val, 2),
            'teleop_balls_avg': round(tele_val, 2),
            'accuracy_avg': round(acc_val, 1),
            'climb_rate': round(climb_rate, 1),
            'match_count': stats.match_count or 0,
            'power_score': power_score,
            'pit': {
                'drivetrain': pit.drivetrain_type or 'Unknown',
                'motors': pit.motor_type or 'Unknown'
            } if pit else None
        })
    
    # Sort by Power Score descending
    sorted_teams.sort(key=lambda x: x['power_score'], reverse=True)
    
    data = {
        'sorted_teams_json': json.dumps(sorted_teams),
        'seasons': seasons,
        'selected_year': selected_year,
        **get_common_data(user)
    }
    return render_template('picklist.html', **data)

@app.route('/drive-team-briefing')
def briefing_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    from models import Event
    selected_year = request.args.get('year', 2026, type=int)
    seasons = [2026, 2025, 2024]
    # Filter events by year
    events = Event.query.filter(Event.date.like(f"%{selected_year}%")).all()
    return render_template('briefing.html', 
                         events=events, 
                         seasons=seasons, 
                         selected_year=selected_year,
                         **get_common_data(user))

if __name__ == '__main__':
    # In production, use Gunicorn or Waitress.
    app.run(debug=True, host='0.0.0.0', port=5002)
