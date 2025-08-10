from flask import Blueprint

# Import all the blueprint modules
from .auth import auth
from .main import main
from .seller import seller
from .admin import admin
from .api import api
from .search import search

# Create a main routes blueprint that registers all other blueprints
routes = Blueprint('routes', __name__)

# Register all blueprints
def init_app(app):
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(seller)
    app.register_blueprint(admin)
    app.register_blueprint(api)
    app.register_blueprint(search)
