from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        # Check if column exists
        sql = text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS partner_id INTEGER REFERENCES "user"(id)')
        db.session.execute(sql)
        db.session.commit()
        print("Column partner_id added successfully (or already exists).")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding column: {e}")
