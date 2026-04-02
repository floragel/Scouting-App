from app import app
from models import User

with app.app_context():
    users = User.query.all()
    for u in users:
        print(f"{u.id}|{u.name}")
