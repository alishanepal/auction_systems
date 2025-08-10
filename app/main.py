from flask import Blueprint, render_template, session
from .models import Product, Auction, Bid, AuctionResult
from .utils import format_indian_currency
from .recommendations import get_recommended_products
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
    
    # Get products for each category (limit to 6 per category)
    live_products = [auction.product for auction in live_auctions[:6]]
    upcoming_products = [auction.product for auction in upcoming_auctions[:6]]
    ended_products = [auction.product for auction in ended_auctions[:6]]
    
    # Get personalized recommendations
    recommended_products = get_recommended_products(user_id, limit=6)
    
    return render_template('home.html', 
                           live_products=live_products,
                           upcoming_products=upcoming_products,
                           ended_products=ended_products,
                           recommended_products=recommended_products,
                           format_indian_currency=format_indian_currency)

@main.route('/auction/<int:auction_id>')
def view_auction(auction_id):
    # Fetch the auction and its associated product
    auction = Auction.query.get_or_404(auction_id)
    product = auction.product
    
    # Get current highest bid
    current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
    current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else product.starting_bid
    
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
                         auction_result=auction_result,
                         winning_bid=winning_bid,
                         format_indian_currency=format_indian_currency)

@main.route('/live')
def live_auction():
    return render_template('live.html')

@main.route('/upcoming')
def upcoming_auction():
    return render_template('upcoming.html')

@main.route('/closed')
def closed_auction():
    return render_template('closed.html')
