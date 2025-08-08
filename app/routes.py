from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from .models import db, User
from sqlalchemy.exc import IntegrityError
from functools import wraps

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html')

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

# Role required decorator
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') != role:
                return redirect(url_for('main.home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@main.route('/api/login', methods=['POST'])
def process_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = User.query.filter((User.username == username) | (User.email == username)).first()
    
    if user and user.check_password(password):
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

@main.route('/logout')
def logout():
    # Clear session
    session.clear()
    return redirect(url_for('main.home'))

# Seller routes
@main.route('/seller/dashboard')
@login_required
@role_required('seller')
def seller_dashboard():
    return render_template('seller_dashboard.html')

@main.route('/seller/create-auction')
@login_required
@role_required('seller')
def create_auction():
    # Get all categories and subcategories for the form
    from .models import Category, Subcategory
    categories = Category.query.all()
    return render_template('create_auction.html', categories=categories)

@main.route('/api/get-subcategories/<int:category_id>')
@login_required
def get_subcategories(category_id):
    from .models import Subcategory
    subcategories = Subcategory.query.filter_by(category_id=category_id).all()
    return jsonify({
        'subcategories': [{'id': sub.id, 'name': sub.name} for sub in subcategories]
    })

# API routes for category management
@main.route('/api/categories', methods=['POST'])
@login_required
@role_required('admin')
def add_category():
    from .models import Category
    category_name = request.form.get('category_name')
    
    if not category_name:
        return jsonify({'success': False, 'message': 'Category name is required'}), 400
    
    # Check if category already exists
    existing_category = Category.query.filter_by(name=category_name).first()
    if existing_category:
        return jsonify({'success': False, 'message': 'Category already exists'}), 400
    
    # Create new category
    new_category = Category(name=category_name)
    db.session.add(new_category)
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Category added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error adding category: {str(e)}'}), 500

@main.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_category(category_id):
    from .models import Category
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'success': False, 'message': 'Category not found'}), 404
    
    category_name = request.form.get('edit_category_name')
    
    if not category_name:
        return jsonify({'success': False, 'message': 'Category name is required'}), 400
    
    # Check if another category with the same name exists
    existing_category = Category.query.filter(Category.name == category_name, Category.id != category_id).first()
    if existing_category:
        return jsonify({'success': False, 'message': 'Another category with this name already exists'}), 400
    
    # Update category
    category.name = category_name
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Category updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating category: {str(e)}'}), 500

@main.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_category(category_id):
    from .models import Category, Subcategory
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'success': False, 'message': 'Category not found'}), 404
    
    # Delete all subcategories first
    subcategories = Subcategory.query.filter_by(category_id=category_id).all()
    for subcategory in subcategories:
        db.session.delete(subcategory)
    
    # Delete the category
    db.session.delete(category)
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Category deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting category: {str(e)}'}), 500

@main.route('/api/subcategories', methods=['POST'])
@login_required
@role_required('admin')
def add_subcategory():
    from .models import Category, Subcategory
    parent_category_id = request.form.get('parent_category')
    subcategory_name = request.form.get('subcategory_name')
    
    if not parent_category_id or not subcategory_name:
        return jsonify({'success': False, 'message': 'Parent category and subcategory name are required'}), 400
    
    # Check if parent category exists
    parent_category = Category.query.get(parent_category_id)
    if not parent_category:
        return jsonify({'success': False, 'message': 'Parent category not found'}), 404
    
    # Check if subcategory already exists in this category
    existing_subcategory = Subcategory.query.filter_by(name=subcategory_name, category_id=parent_category_id).first()
    if existing_subcategory:
        return jsonify({'success': False, 'message': 'Subcategory already exists in this category'}), 400
    
    # Create new subcategory
    new_subcategory = Subcategory(name=subcategory_name, category_id=parent_category_id)
    db.session.add(new_subcategory)
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Subcategory added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error adding subcategory: {str(e)}'}), 500

@main.route('/api/subcategories/<int:subcategory_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_subcategory(subcategory_id):
    from .models import Category, Subcategory
    subcategory = Subcategory.query.get(subcategory_id)
    if not subcategory:
        return jsonify({'success': False, 'message': 'Subcategory not found'}), 404
    
    parent_category_id = request.form.get('edit_subcategory_category')
    subcategory_name = request.form.get('edit_subcategory_name')
    
    if not parent_category_id or not subcategory_name:
        return jsonify({'success': False, 'message': 'Parent category and subcategory name are required'}), 400
    
    # Check if parent category exists
    parent_category = Category.query.get(parent_category_id)
    if not parent_category:
        return jsonify({'success': False, 'message': 'Parent category not found'}), 404
    
    # Check if another subcategory with the same name exists in the same category
    existing_subcategory = Subcategory.query.filter(
        Subcategory.name == subcategory_name, 
        Subcategory.category_id == parent_category_id, 
        Subcategory.id != subcategory_id
    ).first()
    if existing_subcategory:
        return jsonify({'success': False, 'message': 'Another subcategory with this name already exists in this category'}), 400
    
    # Update subcategory
    subcategory.name = subcategory_name
    subcategory.category_id = parent_category_id
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Subcategory updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating subcategory: {str(e)}'}), 500

@main.route('/api/subcategories/<int:subcategory_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_subcategory(subcategory_id):
    from .models import Subcategory
    subcategory = Subcategory.query.get(subcategory_id)
    if not subcategory:
        return jsonify({'success': False, 'message': 'Subcategory not found'}), 404
    
    # Delete the subcategory
    db.session.delete(subcategory)
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Subcategory deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting subcategory: {str(e)}'}), 500

@main.route('/seller/create-auction', methods=['POST'])
@login_required
@role_required('seller')
def process_auction():
    from .models import Product, Auction
    from datetime import datetime
    import os
    from werkzeug.utils import secure_filename
    import uuid
    
    # Get form data
    product_name = request.form.get('product_name')
    starting_bid = request.form.get('starting_bid')
    reserve_price = request.form.get('reserve_price')
    description = request.form.get('description')
    keywords = request.form.get('keywords')
    minimum_interval = request.form.get('minimum_interval')
    category_id = request.form.get('category')
    subcategory_id = request.form.get('subcategory')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    # Validate required fields
    if not all([product_name, starting_bid, category_id, subcategory_id, start_time, end_time]):
        return jsonify({'success': False, 'message': 'Required fields are missing'})
    
    try:
        # Handle image upload
        image_url = None
        if 'image' in request.files and request.files['image'].filename:
            image_file = request.files['image']
            # Generate a unique filename to prevent collisions
            filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            
            # Ensure uploads directory exists
            upload_folder = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(upload_folder, unique_filename)
            image_file.save(file_path)
            
            # Store the relative URL for the database
            image_url = f"uploads/{unique_filename}"
        
        # Create new product
        new_product = Product(
            name=product_name,
            starting_bid=float(starting_bid),
            reserve_price=float(reserve_price) if reserve_price else None,
            description=description,
            keywords=keywords,
            minimum_interval=float(minimum_interval) if minimum_interval else 1.0,
            category_id=int(category_id),
            subcategory_id=int(subcategory_id),
            seller_id=session['user_id'],
            image_url=image_url
        )
        
        db.session.add(new_product)
        db.session.flush()  # Get the product ID
        
        # Parse datetime strings
        start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        
        # Create new auction
        new_auction = Auction(
            product_id=new_product.id,
            start_date=start_datetime,
            end_date=end_datetime,
            status='pending'
        )
        
        db.session.add(new_auction)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Auction created successfully!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating auction: {str(e)}'})


# Admin routes
@main.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@main.route('/admin/categories')
@login_required
@role_required('admin')
def admin_categories():
    # Get all categories with their subcategories
    from .models import Category
    categories = Category.query.all()
    
    return render_template('admin_categories.html', categories=categories)
