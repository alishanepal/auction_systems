from flask import Flask
from flask_migrate import Migrate
import os
from .models import db

def create_app():
    app = Flask(__name__, 
                template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
                static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'static')))
    
    # Database configuration
    app.config['SECRET_KEY'] = 'your-secret-key-here'  # Required for session management
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    from .routes import main
    app.register_blueprint(main)
    
    return app
