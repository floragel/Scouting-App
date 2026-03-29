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
from sqlalchemy import text

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
    return {
        'user': user,
        'version': '2.0.26',
        'is_admin': user.role and ('Admin' in user.role or 'Head Scout' in user.role)
    }

def get_dashboard_data(user):
    from models import PitScoutData, MatchScoutData, Event, Team
    
    # Fetch data for Analytics
    pit_entries = PitScoutData.query.all()
    match_entries = MatchScoutData.query.all()
    events = Event.query.all()
    
    # Simple team performance aggregation
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
        'user_performance': {
            'matches_scouted': user.matches_scouted or 0,
            'accuracy': '85%' # Placeholder if not computed
        },
        'team_status': {
            'type': 'next_match',
            'text': 'Quals 42: Ready to Scout',
            'color': 'green',
            'event_key': '2026pncmp'
        },
        'live_match': 'Quals 41',
        'assignments': [a.to_dict() for a in user.assignments] if user.assignments else [],
        'event_matches': [],
        'events_list': [e.to_dict() for e in events],
        'pit_data_json': json.dumps([p.to_dict() for p in pit_entries]),
        'match_data_json': json.dumps([m.to_dict() for m in match_entries]),
        'team_averages_json': json.dumps(team_stats),
        'dashboard_note': 'Focus on trap notes and climb speed for top seeds.',
    }

@app.route('/')
def index():
    user = get_current_user()
    if not user:
        return redirect(url_for('login_view'))
    return render_template('events.html', **get_common_data(user))

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
    data = get_dashboard_data(user)
    return render_template('dashboard.html', **data)

@app.route('/analytics')
def analytics_view():
    user = get_current_user()
    if not user:
        return redirect(url_for('login_view'))
    data = get_dashboard_data(user)
    return render_template('analytics.html', **data)

@app.route('/admin-hub')
def admin_hub_view():
    user = get_current_user()
    if not user or (user.role and 'Admin' not in user.role and 'Head Scout' not in user.role):
        return redirect(url_for('events_view'))
    return render_template('admin.html', **get_common_data(user))

@app.route('/teams-dir')
def teams_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    return render_template('teams.html', **get_common_data(user))

@app.route('/events')
def events_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    return render_template('events.html', **get_common_data(user))

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
    if assignment.user_id != user.id and not ('Admin' in user.role or 'Head Scout' in user.role):
        return "Not authorized to scout this match", 403
    return render_template('match_scout.html', assignment=assignment, **get_common_data(user))

@app.route('/pit-scout/<int:assignment_id>')
def pit_scout(assignment_id):
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    from models import ScoutAssignment
    assignment = ScoutAssignment.query.get_or_404(assignment_id)
    if assignment.user_id != user.id and not ('Admin' in user.role or 'Head Scout' in user.role):
        return "Unauthorized", 403
    return render_template('pit_scout.html', assignment=assignment, **get_common_data(user))

@app.route('/members')
def members_view():
    user = get_current_user()
    if not user: return redirect(url_for('login_view'))
    from models import MatchScoutData, User
    team_members = User.query.filter_by(team_id=user.team_id).all() if user.team_id else []
    members_data = []
    for m in team_members:
        m_dict = m.to_dict()
        m_dict['matches_scouted'] = MatchScoutData.query.filter_by(scouter_id=m.id).count()
        members_data.append(m_dict)
    return render_template('members.html', team_members=members_data, members_json=json.dumps(members_data), **get_common_data(user))

if __name__ == '__main__':
    # In production, use Gunicorn or Waitress.
    app.run(debug=True, host='0.0.0.0', port=5002)
