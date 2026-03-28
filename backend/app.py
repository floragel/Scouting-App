import os
from dotenv import load_dotenv
from flask import Flask, jsonify

from models import db
from routes import register_blueprints

load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
# Check for DATABASE_URL (often provided by Render or Heroku)
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # SQLAlchemy 1.4+ requires postgresql:// instead of postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback to local SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, '..', 'data', 'scouting.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev_secret_key_scouting_app' # Change in production
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# File upload configuration
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PITS_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'pit_photos')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max upload size
app.config['STRATEGY_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'strategies')

# Ensure upload directory exists
os.makedirs(app.config['PITS_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STRATEGY_UPLOAD_FOLDER'], exist_ok=True)

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

@app.route('/api/migrate')
def manual_migrate():
    results = []
    try:
        from sqlalchemy import text
        # List of columns that might be missing in production
        migrations = [
            ("reset_token", "ALTER TABLE \"user\" ADD COLUMN reset_token VARCHAR(100)"),
            ("reset_token_expiry", "ALTER TABLE \"user\" ADD COLUMN reset_token_expiry TIMESTAMP"),
            ("password_plain", "ALTER TABLE \"user\" ADD COLUMN password_plain VARCHAR(256)"),
            ("last_login", "ALTER TABLE \"user\" ADD COLUMN last_login TIMESTAMP"),
            ("last_active", "ALTER TABLE \"user\" ADD COLUMN last_active TIMESTAMP"),
            ("matches_scouted", "ALTER TABLE \"user\" ADD COLUMN matches_scouted INTEGER DEFAULT 0"),
            ("join_date", "ALTER TABLE \"user\" ADD COLUMN join_date VARCHAR(20)")
        ]
        
        with db.engine.connect() as conn:
            for col, sql in migrations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    results.append(f"SUCCESS: {col}")
                except Exception as e:
                    conn.rollback() # Needed for Postgres after any error
                    results.append(f"SKIP/EXISTING: {col}")
        return jsonify({"status": "Migration complete", "results": results})
    except Exception as e:
        return jsonify({"status": "Migration failed", "error": str(e)})

# Register all routes from blueprints
register_blueprints(app)

# Ensure database tables are created before handling requests
# Gunicorn imports `app` directly, so it skips the __main__ block below.
with app.app_context():
    print("Checking database tables...")
    try:
        db.create_all()
    except Exception as e:
        print(f"db.create_all error: {e}")

    # Migration helper for new columns
    try:
        from sqlalchemy import text
        with db.engine.connect() as conn:
            print("Running database migrations...")
            migrations = [
                ("reset_token", "ALTER TABLE \"user\" ADD COLUMN reset_token VARCHAR(100)"),
                ("reset_token_expiry", "ALTER TABLE \"user\" ADD COLUMN reset_token_expiry TIMESTAMP"),
                ("password_plain", "ALTER TABLE \"user\" ADD COLUMN password_plain VARCHAR(256)"),
                ("last_login", "ALTER TABLE \"user\" ADD COLUMN last_login TIMESTAMP"),
                ("last_active", "ALTER TABLE \"user\" ADD COLUMN last_active TIMESTAMP"),
                ("matches_scouted", "ALTER TABLE \"user\" ADD COLUMN matches_scouted INTEGER DEFAULT 0"),
                ("join_date", "ALTER TABLE \"user\" ADD COLUMN join_date VARCHAR(20)")
            ]
            for col, sql in migrations:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"Added column: {col}")
                except Exception as e: 
                    conn.rollback()
                    print(f"Column {col} already exists or error: {e}")
    except Exception as e:
        print(f"CRITICAL Migration error: {e}")

@app.route('/api/admin/reset-and-init-team')
def reset_and_init_team():
    import datetime
    import unicodedata
    import re
    from werkzeug.security import generate_password_hash
    from models import User, Team, Event, MatchScoutData, PitScoutData, ScoutAssignment

    def slugify(name):
        name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
        name = name.lower().replace(' ', '.').replace('-', '.')
        return re.sub(r'[^a-zA-Z0-9.]', '', name)

    try:
        # 1. Clear Data
        ScoutAssignment.query.delete()
        MatchScoutData.query.delete()
        PitScoutData.query.delete()
        User.query.delete()
        Team.query.delete()
        Event.query.delete()
        db.session.commit()

        # 2. Create Team
        team = Team(team_number=6622, team_name="StanRobotix", access_code="STAN6622", tba_key="frc6622")
        db.session.add(team)
        db.session.commit()

        # 3. Create Users
        DEFAULT_PASS = "FRC6622!"
        MEMBERS = {
            "Head Scout": ["Danaé", "Jisoo"],
            "Pit Scout": ["Saulius", "Lojayen", "Anna", "Pierre"],
            "Stand Scout": [
                "Alexander", "Raphaël A.", "Paul-Hugo", "Clémence", 
                "Marcu", "Julien", "Sofia", "El Ghali", "Noé", "James",
                "Luc", "George", "Théa", "Pauline"
            ]
        }

        created = []
        # Main Admin
        admin = User(
            email="admin@scout.com", name="Admin",
            password_hash=generate_password_hash(DEFAULT_PASS), password_plain=DEFAULT_PASS,
            role="Admin", status="active", team_id=team.id,
            join_date=datetime.datetime.now().strftime("%Y-%m-%d")
        )
        db.session.add(admin)
        created.append("Admin: admin@scout.com")

        for role, names in MEMBERS.items():
            for name in names:
                email = f"{slugify(name)}@scout.com"
                if User.query.filter_by(email=email).first(): continue
                u = User(
                    email=email, name=name,
                    password_hash=generate_password_hash(DEFAULT_PASS), password_plain=DEFAULT_PASS,
                    role=role, status="active", team_id=team.id,
                    join_date=datetime.datetime.now().strftime("%Y-%m-%d")
                )
                db.session.add(u)
                created.append(f"{role}: {name} ({email})")

        db.session.commit()
        return jsonify({"status": "Success", "database": "Reset and Initialized", "members_created": created, "default_password": DEFAULT_PASS})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "Error", "message": str(e)})

if __name__ == '__main__':
    # In production, use Gunicorn or Waitress.
    app.run(debug=True, host='0.0.0.0', port=5002)
