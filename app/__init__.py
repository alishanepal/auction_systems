from flask import Flask
from flask_migrate import Migrate
from flask_socketio import SocketIO
import os
import secrets
from .models import db

# Initialize SocketIO instance
socketio = SocketIO()

def create_app():
    app = Flask(__name__, 
                template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
                static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'static')))
    
    # Database configuration
    app.config['SECRET_KEY'] = secrets.token_hex(16)  # Generate a secure random key for session management
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///auction.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    from .routes import init_app as init_routes
    init_routes(app)
    
    # Initialize SocketIO with the app
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Import and register socket events
    from . import socket_events
    
    return app
