from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    # Drop all tables and recreate them
    db.drop_all()
    db.create_all()
    print('Database tables recreated successfully!')