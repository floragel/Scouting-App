import os
import datetime
import tempfile
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Whisper Voice Transcription ---
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        print("Loading Whisper model...")
        import whisper
        whisper_model = whisper.load_model("base")
    return whisper_model

@auth_bp.route('/api/voice-transcribe', methods=['POST'])
def voice_transcribe():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': 'No audio file selected'}), 400

    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        temp_path = temp_audio.name

    try:
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


# --- Auth Routes ---

@auth_bp.route('/api/auth/register', methods=['POST'])
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
    user = User(email=email, password_hash=password_hash, password_plain=password, name=name, last_login=datetime.datetime.now())
    db.session.add(user)
    db.session.commit()

    session.permanent = True
    session['user_id'] = user.id
    return jsonify({'message': 'Registered and logged in successfully.', 'user': user.to_dict()}), 201

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    session.permanent = True
    session['user_id'] = user.id
    user.last_login = datetime.datetime.now()
    db.session.commit()
    return jsonify({'message': 'Logged in successfully', 'user': user.to_dict()}), 200

@auth_bp.route('/api/auth/setup-admin', methods=['POST'])
def setup_admin():
    # Only allow if SETUP_SECRET is defined in environment to prevent abuse
    expected_secret = os.environ.get('SETUP_SECRET')
    if not expected_secret:
        return jsonify({'error': 'Setup endpoint is disabled. Contact server administrator.'}), 403
        
    data = request.json
    provided_secret = data.get('setup_secret')
    email = data.get('email')
    team_number = data.get('team_number')
    
    if not provided_secret or str(provided_secret).strip() != str(expected_secret).strip():
        return jsonify({'error': 'Invalid setup secret'}), 401
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found. Register an account first.'}), 404
        
    from models import Team, db
    import secrets, string
    
    team = Team.query.filter_by(team_number=team_number).first()
    if not team:
        new_code = f"{''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))}{team_number}"
        team = Team(team_number=team_number, tba_key=f"frc{team_number}", team_name=f"Team {team_number}", nickname=f"Team {team_number}", access_code=new_code)
        db.session.add(team)
        db.session.commit()
    elif not team.tba_key:
        team.tba_key = f"frc{team_number}"
        db.session.commit()
        
    user.role = 'Admin'
    user.status = 'active'
    user.team_id = team.id
    db.session.commit()
    
    return jsonify({
        'message': f"Success! {email} is now an Admin.",
        'team_access_code': team.access_code
    }), 200

@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal if email exists or not for security
        return jsonify({'message': 'If this email exists, a reset link has been generated. Check with your admin.'}), 200
    
    import secrets
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
    db.session.commit()
    
    # Print the reset link to the server console (no email server needed)
    reset_url = f"/reset-password?token={token}"
    print(f"\n{'='*60}")
    print(f"🔑 PASSWORD RESET for {email}")
    print(f"   Reset URL: {reset_url}")
    print(f"   Token expires in 1 hour")
    print(f"{'='*60}\n")
    
    return jsonify({
        'message': 'If this email exists, a reset link has been generated.',
        'reset_url': reset_url  # In production, remove this and send by email
    }), 200

@auth_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    token = data.get('token')
    new_password = data.get('new_password')
    
    if not token or not new_password:
        return jsonify({'error': 'Token and new password are required'}), 400
    
    if len(new_password) < 3:
        return jsonify({'error': 'Password must be at least 3 characters'}), 400
    
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        return jsonify({'error': 'Invalid or expired reset token'}), 400
    
    if user.reset_token_expiry and user.reset_token_expiry < datetime.datetime.now():
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        return jsonify({'error': 'Reset token has expired. Please request a new one.'}), 400
    
    user.password_hash = generate_password_hash(new_password)
    user.password_plain = new_password
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()
    
    return jsonify({'message': 'Password reset successfully. You can now log in.'}), 200

@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/api/user/me', methods=['GET', 'PUT'])
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

        if 'new_password' in data and data['new_password']:
            current_pass = data.get('current_password')
            if not current_pass or not check_password_hash(user.password_hash, current_pass):
                return jsonify({'error': 'Current password is incorrect'}), 400
            user.password_hash = generate_password_hash(data['new_password'])
            user.password_plain = data['new_password']

        db.session.commit()
        return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200

    return jsonify(user.to_dict()), 200

@auth_bp.route('/api/user/upload-profile-picture', methods=['POST'])
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
        filename = f"{user.id}_{filename}"
        upload_path = os.path.join(basedir, 'static', 'uploads', 'profiles')
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, filename))

        user.profile_picture = f"/static/uploads/profiles/{filename}"
        db.session.commit()

        return jsonify({'message': 'Profile picture uploaded successfully', 'url': user.profile_picture}), 200
