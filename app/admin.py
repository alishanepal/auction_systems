from flask import Blueprint, render_template, request, jsonify, session
from .models import db, User, Product, Auction, Bid, Category, Subcategory
from .utils import login_required, role_required, format_indian_currency
from datetime import datetime, timedelta

admin = Blueprint('admin', __name__)

@admin.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
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

@admin.route('/admin/categories')
@login_required
@role_required('admin')
def admin_categories():
    # Get all categories with their subcategories
    categories = Category.query.all()
    
    return render_template('admin_categories.html', categories=categories)

# API routes for category management
@admin.route('/api/categories', methods=['POST'])
@login_required
@role_required('admin')
def add_category():
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

@admin.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_category(category_id):
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

@admin.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_category(category_id):
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

@admin.route('/api/subcategories', methods=['POST'])
@login_required
@role_required('admin')
def add_subcategory():
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

@admin.route('/api/subcategories/<int:subcategory_id>', methods=['PUT'])
@login_required
@role_required('admin')
def update_subcategory(subcategory_id):
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

@admin.route('/api/subcategories/<int:subcategory_id>', methods=['DELETE'])
@login_required
@role_required('admin')
def delete_subcategory(subcategory_id):
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

# Sellers Report Route
@admin.route('/admin/sellers-report')
@login_required
@role_required('admin')
def admin_sellers_report():
    # Get all sellers with their status and statistics
    sellers = User.query.filter_by(role='seller').order_by(User.created_at.desc()).all()
    
    # Separate sellers by status
    pending_sellers = [user for user in sellers if user.status == 'pending']
    accepted_sellers = [user for user in sellers if user.status == 'accepted']
    rejected_sellers = [user for user in sellers if user.status == 'rejected']
    
    # Calculate statistics for each seller
    for seller in sellers:
        seller.total_products = len(seller.products)
        seller.total_auctions = sum(len(product.auctions) for product in seller.products)
        seller.total_revenue = sum(
            auction.result.winning_bid if auction.result else 0 
            for product in seller.products 
            for auction in product.auctions
        )
    
    return render_template('admin_sellers_report.html',
                         pending_sellers=pending_sellers,
                         accepted_sellers=accepted_sellers,
                         rejected_sellers=rejected_sellers,
                         format_indian_currency=format_indian_currency)

# Bidders Report Route
@admin.route('/admin/bidders-report')
@login_required
@role_required('admin')
def admin_bidders_report():
    # Get all bidders with their status and statistics
    bidders = User.query.filter_by(role='bidder').order_by(User.created_at.desc()).all()
    
    # Separate bidders by status
    pending_bidders = [user for user in bidders if user.status == 'pending']
    accepted_bidders = [user for user in bidders if user.status == 'accepted']
    rejected_bidders = [user for user in bidders if user.status == 'rejected']
    
    # Calculate statistics for each bidder
    for bidder in bidders:
        bidder.total_bids = len(bidder.bids)
        bidder.won_auctions_count = len(bidder.won_auctions)
        bidder.total_spent = sum(auction_result.winning_bid for auction_result in bidder.won_auctions)
    
    return render_template('admin_bidders_report.html',
                         pending_bidders=pending_bidders,
                         accepted_bidders=accepted_bidders,
                         rejected_bidders=rejected_bidders,
                         format_indian_currency=format_indian_currency)

# Products Report Route
@admin.route('/admin/products-report')
@login_required
@role_required('admin')
def admin_products_report():
    # Get all products with their statistics
    products = Product.query.order_by(Product.created_at.desc()).all()
    
    # Calculate statistics for each product
    for product in products:
        product.total_auctions = len(product.auctions)
        product.total_bids = sum(len(auction.bids) for auction in product.auctions)
        product.highest_bid = max(
            (bid.amount for auction in product.auctions for bid in auction.bids),
            default=0
        )
        product.total_revenue = sum(
            auction.result.winning_bid if auction.result else 0
            for auction in product.auctions
        )
    
    return render_template('admin_products_report.html',
                         products=products,
                         format_indian_currency=format_indian_currency)

# Winners Report Route
@admin.route('/admin/winners-report')
@login_required
@role_required('admin')
def admin_winners_report():
    # Get all auction results (winners)
    auction_results = AuctionResult.query.order_by(AuctionResult.created_at.desc()).all()
    
    # Get additional information for each result
    for result in auction_results:
        result.product_name = result.auction.product.name if result.auction and result.auction.product else 'Unknown'
        result.seller_name = result.auction.product.seller.username if result.auction and result.auction.product and result.auction.product.seller else 'Unknown'
        result.winner_name = result.winner.username if result.winner else 'Unknown'
        result.auction_title = result.auction.title if result.auction else 'Unknown'
    
    return render_template('admin_winners_report.html',
                         auction_results=auction_results,
                         format_indian_currency=format_indian_currency)

# User Approval/Rejection API Routes
@admin.route('/api/users/<int:user_id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    user.status = 'accepted'
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {user.username} approved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error approving user: {str(e)}'}), 500

@admin.route('/api/users/<int:user_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Delete the user from database
    db.session.delete(user)
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'User {user.username} rejected and deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error rejecting user: {str(e)}'}), 500
