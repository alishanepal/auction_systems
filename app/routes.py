from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from .models import db, User
from sqlalchemy.exc import IntegrityError
from functools import wraps

def format_indian_currency(amount):
    """Format amount in Indian currency style (1,00,000.00)"""
    if amount is None:
        return "Rs 0.00"
    
    # Convert to string with 2 decimal places
    amount_str = f"{amount:.2f}"
    
    # Split into integer and decimal parts
    parts = amount_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1]
    
    # Indian numbering system: group from right
    # Last 3 digits together, then groups of 2 digits
    if len(integer_part) <= 3:
        formatted_integer = integer_part
    else:
        # Take last 3 digits
        last_three = integer_part[-3:]
        # Take remaining digits
        remaining = integer_part[:-3]
        
        # Add commas every 2 digits from right for remaining part
        formatted_remaining = ""
        for i in range(len(remaining)):
            if i > 0 and i % 2 == 0:
                formatted_remaining = "," + formatted_remaining
            formatted_remaining = remaining[-(i+1)] + formatted_remaining
        
        formatted_integer = formatted_remaining + "," + last_three
    
    return f"Rs {formatted_integer}.{decimal_part}"

main = Blueprint('main', __name__)

@main.route('/')
def home():
    # Fetch products with auctions to display on the home page
    from .models import Product, Auction
    from sqlalchemy import desc
    from datetime import datetime
    
    now = datetime.utcnow()
    
    # Get all auctions
    auctions = Auction.query.all()
    
    # Categorize auctions by status
    live_auctions = []
    upcoming_auctions = []
    ended_auctions = []
    
    for auction in auctions:
        if auction.status == 'live':
            live_auctions.append(auction)
        elif auction.status == 'upcoming':
            upcoming_auctions.append(auction)
        else:  # ended
            ended_auctions.append(auction)
    
    # Get products for each category (limit to 6 per category)
    live_products = [auction.product for auction in live_auctions[:6]]
    upcoming_products = [auction.product for auction in upcoming_auctions[:6]]
    ended_products = [auction.product for auction in ended_auctions[:6]]
    
    return render_template('home.html', 
                           live_products=live_products,
                           upcoming_products=upcoming_products,
                           ended_products=ended_products,
                           format_indian_currency=format_indian_currency)

@main.route('/auction/<int:auction_id>')
def view_auction(auction_id):
    # Fetch the auction and its associated product
    from .models import Auction, Product, Bid
    
    auction = Auction.query.get_or_404(auction_id)
    product = auction.product
    
    # Get current highest bid
    current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
    current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else product.starting_bid
    
    return render_template('view_auction.html', 
                         auction=auction, 
                         product=product, 
                         current_highest_bid=current_highest_bid,
                         current_highest_amount=current_highest_amount,
                         format_indian_currency=format_indian_currency)

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

@main.route('/logout')
def logout():
    # Clear session variables
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    
    # Redirect to home page
    return redirect(url_for('main.home'))

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

# Removed duplicate logout route

# Seller routes
@main.route('/seller/dashboard')
@login_required
@role_required('seller')
def seller_dashboard():
    from .models import Product, Auction, Bid
    from datetime import datetime
    
    # Get seller's products and auctions
    seller_id = session['user_id']
    products = Product.query.filter_by(seller_id=seller_id).all()
    
    # Get all auctions for this seller
    auctions = []
    for product in products:
        for auction in product.auctions:
            auctions.append(auction)
    
    # Categorize auctions by status
    live_auctions = []
    upcoming_auctions = []
    ended_auctions = []
    
    for auction in auctions:
        if auction.status == 'live':
            live_auctions.append(auction)
        elif auction.status == 'upcoming':
            upcoming_auctions.append(auction)
        else:  # ended
            ended_auctions.append(auction)
    
    # Calculate statistics
    total_products = len(products)
    total_auctions = len(auctions)
    total_bids = sum(len(auction.bids) for auction in auctions)
    total_revenue = 0
    
    # Calculate revenue from ended auctions with bids
    for auction in ended_auctions:
        if auction.bids:
            highest_bid = max(auction.bids, key=lambda x: x.bid_amount)
            total_revenue += highest_bid.bid_amount
    
    return render_template('seller_dashboard.html', 
                         products=products,
                         live_auctions=live_auctions,
                         upcoming_auctions=upcoming_auctions,
                         ended_auctions=ended_auctions,
                         total_products=total_products,
                         total_auctions=total_auctions,
                         total_bids=total_bids,
                         total_revenue=total_revenue,
                         format_indian_currency=format_indian_currency)

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
    category_id = request.form.get('category')
    subcategory_id = request.form.get('subcategory')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    # Calculate minimum interval as 5% of starting bid
    minimum_interval = float(starting_bid) * 0.05 if starting_bid else 1.0
    
    # Validate required fields
    if not all([product_name, starting_bid, category_id, subcategory_id, start_time, end_time]):
        return jsonify({'success': False, 'message': 'Required fields are missing'})
    
    try:
        # Parse datetime strings
        start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        now = datetime.utcnow()
        
        # Validate start and end times
        if start_datetime < now:
            return jsonify({'success': False, 'message': 'Start time cannot be in the past'})
        
        if end_datetime <= start_datetime:
            return jsonify({'success': False, 'message': 'End time must be after start time'})
        
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
        
        # Determine initial status based on start time
        initial_status = 'upcoming'
        if start_datetime <= now < end_datetime:
            initial_status = 'live'
        
        # Create new auction
        new_auction = Auction(
            product_id=new_product.id,
            start_date=start_datetime,
            end_date=end_datetime,
            status=initial_status
        )
        
        db.session.add(new_auction)
        db.session.commit()
        
        # Notify connected clients about the new auction
        from . import socketio
        socketio.emit('new_auction', {
            'id': new_auction.id,
            'product_name': new_product.name,
            'status': new_auction.status,
            'start_date': start_datetime.isoformat(),
            'end_date': end_datetime.isoformat()
        })
        
        return jsonify({'success': True, 'message': 'Auction created successfully!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating auction: {str(e)}'})


# Admin routes
@main.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    from .models import User, Product, Auction, Bid, Category, Subcategory
    from datetime import datetime, timedelta
    
    # Get system statistics
    total_users = User.query.count()
    total_bidders = User.query.filter_by(role='bidder').count()
    total_sellers = User.query.filter_by(role='seller').count()
    total_products = Product.query.count()
    total_categories = Category.query.count()
    total_subcategories = Subcategory.query.count()
    
    # Get auction statistics
    all_auctions = Auction.query.all()
    live_auctions = [a for a in all_auctions if a.status == 'live']
    upcoming_auctions = [a for a in all_auctions if a.status == 'upcoming']
    ended_auctions = [a for a in all_auctions if a.status == 'ended']
    
    # Get bid statistics
    total_bids = Bid.query.count()
    total_revenue = 0
    
    # Calculate total revenue from ended auctions
    for auction in ended_auctions:
        if auction.bids:
            highest_bid = max(auction.bids, key=lambda x: x.bid_amount)
            total_revenue += highest_bid.bid_amount
    
    # Get recent activities
    recent_users = User.query.order_by(User.id.desc()).limit(5).all()
    recent_auctions = Auction.query.order_by(Auction.created_at.desc()).limit(5).all()
    recent_bids = Bid.query.order_by(Bid.bid_time.desc()).limit(10).all()
    
    # Get top performing categories
    category_stats = []
    for category in Category.query.all():
        category_products = Product.query.filter_by(category_id=category.id).count()
        category_stats.append({
            'name': category.name,
            'products': category_products
        })
    
    # Sort categories by product count
    category_stats.sort(key=lambda x: x['products'], reverse=True)
    top_categories = category_stats[:5]
    
    return render_template('admin_dashboard.html',
                         total_users=total_users,
                         total_bidders=total_bidders,
                         total_sellers=total_sellers,
                         total_products=total_products,
                         total_categories=total_categories,
                         total_subcategories=total_subcategories,
                         live_auctions=len(live_auctions),
                         upcoming_auctions=len(upcoming_auctions),
                         ended_auctions=len(ended_auctions),
                         total_bids=total_bids,
                         total_revenue=total_revenue,
                         recent_users=recent_users,
                         recent_auctions=recent_auctions,
                         recent_bids=recent_bids,
                         top_categories=top_categories,
                         format_indian_currency=format_indian_currency)

@main.route('/admin/categories')
@login_required
@role_required('admin')
def admin_categories():
    # Get all categories with their subcategories
    from .models import Category
    categories = Category.query.all()
    
    return render_template('admin_categories.html', categories=categories)


@main.route('/api/place-bid', methods=['POST'])
@login_required
@role_required('bidder')
def place_bid():
    from .models import Bid, Auction, Product
    
    auction_id = request.form.get('auction_id')
    bid_amount = request.form.get('bid_amount')
    
    if not auction_id or not bid_amount:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    try:
        auction_id = int(auction_id)
        bid_amount = float(bid_amount)
        
        # Get the auction and product
        auction = Auction.query.get(auction_id)
        if not auction:
            return jsonify({'success': False, 'message': 'Auction not found'})
        
        # Check if auction is live
        if auction.status != 'live':
            return jsonify({'success': False, 'message': 'Auction is not currently live'})
        
        # Get the current highest bid
        current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
        current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else auction.product.starting_bid
        
        # Calculate minimum bid amount
        minimum_bid = current_highest_amount + auction.product.minimum_interval
        
        # Validate bid amount
        if bid_amount < minimum_bid:
            return jsonify({'success': False, 'message': f'Bid must be at least {format_indian_currency(minimum_bid)}'})
        
        # Check if user is not bidding on their own auction
        if auction.product.seller_id == session['user_id']:
            return jsonify({'success': False, 'message': 'You cannot bid on your own auction'})
        
        # Check if current user is the last bidder (prevent consecutive bids)
        if current_highest_bid and current_highest_bid.bidder_id == session['user_id']:
            return jsonify({'success': False, 'message': 'You cannot place consecutive bids. Please wait for another user to bid first.'})
        
        # Create new bid
        new_bid = Bid(
            auction_id=auction_id,
            bidder_id=session['user_id'],
            bid_amount=bid_amount
        )
        
        db.session.add(new_bid)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Bid of {format_indian_currency(bid_amount)} placed successfully!',
            'new_highest_bid': bid_amount,
            'new_minimum_bid': bid_amount + auction.product.minimum_interval
        })
        
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid bid amount'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error placing bid: {str(e)}'})
