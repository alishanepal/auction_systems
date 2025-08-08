from app import create_app
from app.models import db, User

app = create_app()

with app.app_context():
    # Check if admin already exists
    admin = User.query.filter_by(username='admin').first()
    
    if not admin:
        # Create admin user
        admin_user = User(username='admin', email='admin@example.com', role='admin')
        admin_user.set_password('admin123')
        
        # Add to database
        db.session.add(admin_user)
        db.session.commit()
        
        print('Admin user created successfully!')
    else:
        print('Admin user already exists!')