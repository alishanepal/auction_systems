from flask import Blueprint, render_template, request, jsonify
from .models import db, User
from sqlalchemy.exc import IntegrityError

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html')

@main.route('/api/login', methods=['POST'])
def process_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = User.query.filter((User.username == username) | (User.email == username)).first()
    
    if user and user.check_password(password):
        response = {'success': True, 'message': 'Login successful'}
    else:
        response = {'success': False, 'message': 'Invalid username or password'}
    
    return jsonify(response)

@main.route('/api/signup', methods=['POST'])
def process_signup():
    username = request.form.get('username')
    email = request.form.get('email')
    role = request.form.get('role')
    password = request.form.get('password')
    
    # Validate input
    if not all([username, email, role, password]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    if role not in ['bidder', 'seller']:
        return jsonify({'success': False, 'message': 'Invalid role'})
    
    try:
        # Create new user
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful!'})
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': 'Username or email already exists. Please choose different ones.'
        })

@main.route('/live')
def live_auction():
    return render_template('live.html')

@main.route('/upcoming')
def upcoming_auction():
    return render_template('upcoming.html')

@main.route('/closed')
def closed_auction():
    return render_template('closed.html')
