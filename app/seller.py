from flask import Blueprint, render_template, request, jsonify, session, current_app
from .models import db, Product, Auction, Bid, Category, Subcategory
from .utils import login_required, role_required, format_indian_currency, calculate_minimum_increment
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import uuid

seller = Blueprint('seller', __name__)

@seller.route('/seller/dashboard')
@login_required
@role_required('seller')
def seller_dashboard():
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
    
    # Calculate revenue from ended auctions with bids and prepare auction data
    for auction in ended_auctions:
        if auction.bids:
            highest_bid = max(auction.bids, key=lambda x: x.bid_amount)
            total_revenue += highest_bid.bid_amount
            # Add highest_bid attribute to auction object for template use
            auction.highest_bid = highest_bid
        else:
            auction.highest_bid = None
    
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

@seller.route('/seller/create-auction')
@login_required
@role_required('seller')
def create_auction():
    # Get all categories and subcategories for the form
    categories = Category.query.all()
    return render_template('create_auction.html', categories=categories)

@seller.route('/api/get-subcategories/<int:category_id>')
@login_required
def get_subcategories(category_id):
    subcategories = Subcategory.query.filter_by(category_id=category_id).all()
    return jsonify({
        'subcategories': [{'id': sub.id, 'name': sub.name} for sub in subcategories]
    })

@seller.route('/seller/test-json')
@login_required
@role_required('seller')
def test_json():
    """Test route to verify JSON responses work"""
    return jsonify({'success': True, 'message': 'JSON test successful'})

@seller.route('/seller/create-auction', methods=['POST'])
@login_required
@role_required('seller')
def process_auction():
    print("=== process_auction function called ===")
    print(f"Request method: {request.method}")
    print(f"Request content type: {request.content_type}")
    
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
    
    # Debug: Print form data
    print(f"Form data received: {dict(request.form)}")
    print(f"Files received: {dict(request.files)}")
    
    # Calculate minimum interval based on tiered brackets
    minimum_interval = calculate_minimum_increment(float(starting_bid)) if starting_bid else 1.0
    
    # Validate required fields
    if not all([product_name, starting_bid, category_id, subcategory_id, start_time, end_time]):
        return jsonify({'success': False, 'message': 'Required fields are missing'})
    
    try:
        # Parse datetime strings
        print(f"Parsing start_time: {start_time}")
        print(f"Parsing end_time: {end_time}")
        
        start_datetime = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        now = datetime.now()
        
        print(f"Parsed start_datetime: {start_datetime}")
        print(f"Parsed end_datetime: {end_datetime}")
        
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
        print(f"Creating product with seller_id: {session['user_id']}")
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
        
        print(f"Product created: {new_product}")
        db.session.add(new_product)
        db.session.flush()  # Get the product ID
        print(f"Product ID after flush: {new_product.id}")
        
        # Create new auction
        print(f"Creating auction for product_id: {new_product.id}")
        new_auction = Auction(
            product_id=new_product.id,
            start_date=start_datetime,
            end_date=end_datetime
        )
        
        print(f"Auction created: {new_auction}")
        db.session.add(new_auction)
        db.session.commit()
        print(f"Auction committed successfully")
        
        # Notify connected clients about the new auction
        print("About to emit socketio event")
        from . import socketio
        socketio.emit('new_auction', {
            'id': new_auction.id,
            'product_name': new_product.name,
            'status': new_auction.status,
            'start_date': start_datetime.isoformat(),
            'end_date': end_datetime.isoformat()
        })
        print("Socketio event emitted successfully")
        
        return jsonify({'success': True, 'message': 'Auction created successfully!'})
        
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating auction: {str(e)}'})
