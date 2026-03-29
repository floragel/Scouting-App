import os
import sys

# Crucial for Vercel: ensure the backend directory is in sys.path
# so that "from models import db" and other imports work correctly.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
import cloudinary
import cloudinary.uploader

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

if __name__ == '__main__':
    # In production, use Gunicorn or Waitress.
    app.run(debug=True, host='0.0.0.0', port=5002)
