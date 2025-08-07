from flask import Blueprint, render_template, request, jsonify

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html')

@main.route('/api/login', methods=['POST'])
def process_login():
    username = request.form.get('username')
    password = request.form.get('password')
    # Add your login logic here
    response = {'success': True, 'message': 'Login successful'}
    return jsonify(response)

@main.route('/api/signup', methods=['POST'])
def process_signup():
    username = request.form.get('username')
    email = request.form.get('email')
    role = request.form.get('role')
    password = request.form.get('password')
    # Add your signup logic here
    response = {'success': True, 'message': 'Signup successful'}
    return jsonify(response)

@main.route('/live')
def live_auction():
    return render_template('live.html')

@main.route('/upcoming')
def upcoming_auction():
    return render_template('upcoming.html')

@main.route('/closed')
def closed_auction():
    return render_template('closed.html')
