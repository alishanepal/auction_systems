from flask import Blueprint, render_template, session
from .models import db, Product, Auction, Bid, AuctionResult, Wishlist
from .utils import format_indian_currency, calculate_minimum_increment
from .recommendations import get_recommended_products, sort_products_for_user
from sqlalchemy import desc
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def home():
    # Get user ID from session
    user_id = session.get('user_id')
    
    # Fetch products with auctions to display on the home page
    now = datetime.now()
    
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
    
    # Get products for each section, prioritized by user's bid categories and cosine similarity
    live_products_all = [auction.product for auction in live_auctions]
    upcoming_products_all = [auction.product for auction in upcoming_auctions]
    live_products = sort_products_for_user(live_products_all, user_id, limit=6)
    upcoming_products = sort_products_for_user(upcoming_products_all, user_id, limit=6)
    ended_products = [auction.product for auction in ended_auctions[:6]]
    
    # Get personalized recommendations
    recommended_products = get_recommended_products(user_id, limit=6)

    # Compute trending auctions:
    # - For live: by number of bids
    # - For upcoming: by wishlist entries
    live_trending = (
        db.session.query(Auction, db.func.count(Bid.id).label('bid_count'))
        .outerjoin(Bid, Bid.auction_id == Auction.id)
        .filter(Auction.start_date <= datetime.now(), Auction.end_date > datetime.now())
        .group_by(Auction.id)
        .order_by(db.desc('bid_count'))
        .limit(6)
        .all()
    )
    upcoming_trending = (
        db.session.query(Auction, db.func.count(Wishlist.id).label('wish_count'))
        .outerjoin(Wishlist, Wishlist.product_id == Auction.product_id)
        .filter(Auction.start_date > datetime.now())
        .group_by(Auction.id)
        .order_by(db.desc('wish_count'))
        .limit(6)
        .all()
    )

    trending_auctions = [a for a, _ in live_trending] + [a for a, _ in upcoming_trending]

    # Wishlist ids for current user (used by wishlist buttons in upcoming section)
    user_wishlist_product_ids = set()
    if user_id:
        user_wishlist_product_ids = {w.product_id for w in Wishlist.query.filter_by(user_id=user_id).all()}

    return render_template('home.html', 
                           live_products=live_products,
                           upcoming_products=upcoming_products,
                           ended_products=ended_products,
                           recommended_products=recommended_products,
                           trending_auctions=trending_auctions,
                           user_wishlist_product_ids=user_wishlist_product_ids,
                           format_indian_currency=format_indian_currency)


@main.route('/trending')
def trending_page():
    # Compose trending lists again for explicit trending page
    live_trending = (
        db.session.query(Auction, db.func.count(Bid.id).label('bid_count'))
        .outerjoin(Bid, Bid.auction_id == Auction.id)
        .filter(Auction.start_date <= datetime.now(), Auction.end_date > datetime.now())
        .group_by(Auction.id)
        .order_by(db.desc('bid_count'))
        .limit(12)
        .all()
    )
    upcoming_trending = (
        db.session.query(Auction, db.func.count(Wishlist.id).label('wish_count'))
        .outerjoin(Wishlist, Wishlist.product_id == Auction.product_id)
        .filter(Auction.start_date > datetime.now())
        .group_by(Auction.id)
        .order_by(db.desc('wish_count'))
        .limit(12)
        .all()
    )

    user_id = session.get('user_id')
    live_products = [a.product for a, _ in live_trending]
    upcoming_products = [a.product for a, _ in upcoming_trending]
    user_wishlist_product_ids = set()
    if user_id:
        user_wishlist_product_ids = {w.product_id for w in Wishlist.query.filter_by(user_id=user_id).all()}
    return render_template('trending.html',
                           live_products=live_products,
                           upcoming_products=upcoming_products,
                           user_wishlist_product_ids=user_wishlist_product_ids,
                           format_indian_currency=format_indian_currency)

@main.route('/auction/<int:auction_id>')
def view_auction(auction_id):
    # Fetch the auction and its associated product
    auction = Auction.query.get_or_404(auction_id)
    product = auction.product
    
    # Get current highest bid
    current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
    current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else product.starting_bid
    initial_increment = calculate_minimum_increment(current_highest_amount)
    
    # Get auction result if auction has ended
    auction_result = None
    winning_bid = None
    if auction.status == 'ended':
        auction_result = AuctionResult.query.filter_by(auction_id=auction_id).first()
        if auction_result:
            winning_bid = Bid.query.filter_by(
                auction_id=auction_id, 
                bidder_id=auction_result.winner_id,
                bid_amount=auction_result.winning_bid
            ).first()
    
    return render_template('view_auction.html', 
                         auction=auction, 
                         product=product, 
                         current_highest_bid=current_highest_bid,
                         current_highest_amount=current_highest_amount,
                          initial_increment=initial_increment,
                         auction_result=auction_result,
                         winning_bid=winning_bid,
                         format_indian_currency=format_indian_currency)

@main.route('/live')
def live_auction():
    user_id = session.get('user_id')
    live_auctions = Auction.query.filter(
        Auction.start_date <= datetime.now(),
        Auction.end_date > datetime.now()
    ).all()
    products = [a.product for a in live_auctions]
    return render_template('live.html', products=products, format_indian_currency=format_indian_currency)

@main.route('/upcoming')
def upcoming_auction():
    user_id = session.get('user_id')
    upcoming_auctions = Auction.query.filter(
        Auction.start_date > datetime.now()
    ).all()
    products = [a.product for a in upcoming_auctions]
    user_wishlist_product_ids = set()
    if user_id:
        user_wishlist_product_ids = {w.product_id for w in Wishlist.query.filter_by(user_id=user_id).all()}
    return render_template('upcoming.html', products=products, user_wishlist_product_ids=user_wishlist_product_ids, format_indian_currency=format_indian_currency)

@main.route('/closed')
def closed_auction():
    ended_auctions = Auction.query.filter(
        Auction.end_date <= datetime.now()
    ).all()
    products = [a.product for a in ended_auctions]
    return render_template('closed.html', products=products, format_indian_currency=format_indian_currency)
