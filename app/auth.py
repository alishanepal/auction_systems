from flask import Blueprint, request, jsonify, session, redirect, url_for
from .models import db, User
from sqlalchemy.exc import IntegrityError
from .utils import login_required

auth = Blueprint('auth', __name__)

@auth.route('/api/login', methods=['POST'])
def process_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = User.query.filter((User.username == username) | (User.email == username)).first()
    
    if user and user.check_password(password):
        # Check if user is accepted
        if user.status != 'accepted':
            if user.status == 'pending':
                return jsonify({'success': False, 'message': 'Your account is pending approval. Please wait for admin approval.'})
            elif user.status == 'rejected':
                return jsonify({'success': False, 'message': 'Your account has been rejected. Please contact admin for more information.'})
        
        # Set session variables
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        
        # Redirect based on role
        redirect_url = '/'
        if user.role == 'seller':
            redirect_url = '/seller/dashboard'
        elif user.role == 'admin':
            redirect_url = '/admin/dashboard'
            
        response = {
            'success': True, 
            'message': 'Login successful', 
            'redirect': redirect_url
        }
    else:
        response = {'success': False, 'message': 'Invalid username or password'}
        
    return jsonify(response)

@auth.route('/logout')
def logout():
    # Clear session variables
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    
    # Redirect to home page
    return redirect(url_for('main.home'))

@auth.route('/api/signup', methods=['POST'])
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
        # Create new user with pending status
        new_user = User(username=username, email=email, role=role, status='pending')
        new_user.set_password(password)
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful! Your account is pending admin approval. You will be able to login once approved.'})
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False, 
            'message': 'Username or email already exists. Please choose different ones.'
        })
