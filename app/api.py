from flask import Blueprint, request, jsonify, session
from .models import db, Bid, Auction, Product, AuctionResult, Wishlist
from .utils import login_required, role_required, format_indian_currency
from .recommendations import update_bid_history
from datetime import datetime

api = Blueprint('api', __name__)

@api.route('/api/place-bid', methods=['POST'])
@login_required
@role_required('bidder')
def place_bid():
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
        
        # Update bid history for recommendations
        update_bid_history(session['user_id'], auction.product_id, auction_id, bid_amount)
        
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


@api.route('/api/wishlist/toggle', methods=['POST'])
@login_required
@role_required('bidder')
def toggle_wishlist():
    product_id = request.form.get('product_id')
    if not product_id:
        return jsonify({'success': False, 'message': 'Missing product_id'})
    try:
        product_id = int(product_id)
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'})

        # Ensure it's tied to an upcoming auction
        upcoming = Auction.query.filter_by(product_id=product_id).filter(
            Auction.start_date > datetime.now()
        ).first()
        if not upcoming:
            return jsonify({'success': False, 'message': 'Wishlist is only available for upcoming auctions'})

        existing = Wishlist.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({'success': True, 'wishlisted': False})
        else:
            new_w = Wishlist(user_id=session['user_id'], product_id=product_id)
            db.session.add(new_w)
            db.session.commit()
            return jsonify({'success': True, 'wishlisted': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@api.route('/api/process-auction-results', methods=['POST'])
@login_required
@role_required('admin')
def api_process_auction_results():
    """API endpoint to manually process auction results"""
    try:
        processed_count = process_auction_results()
        return jsonify({
            'success': True, 
            'message': f'Processed {processed_count} auction results',
            'processed_count': processed_count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error processing auction results: {str(e)}'})

def process_auction_results():
    """Process auction results for ended auctions that don't have results yet"""
    # Get all ended auctions that don't have results yet
    ended_auctions = Auction.query.filter(
        Auction.end_date < datetime.now(),
        ~Auction.id.in_(
            db.session.query(AuctionResult.auction_id).distinct()
        )
    ).all()
    
    for auction in ended_auctions:
        # Get the highest bid for this auction
        highest_bid = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.bid_amount.desc()).first()
        
        if highest_bid:
            # Check if the bid meets the reserve price (if any)
            if not auction.product.reserve_price or highest_bid.bid_amount >= auction.product.reserve_price:
                # Create auction result
                auction_result = AuctionResult(
                    auction_id=auction.id,
                    winner_id=highest_bid.bidder_id,
                    winning_bid=highest_bid.bid_amount,
                    ended_at=datetime.now()
                )
                db.session.add(auction_result)
            else:
                # Reserve price not met - no winner
                auction_result = AuctionResult(
                    auction_id=auction.id,
                    winner_id=None,  # No winner
                    winning_bid=highest_bid.bid_amount,  # Store the actual highest bid amount
                    ended_at=datetime.now()
                )
                db.session.add(auction_result)
        else:
            # No bids placed - no winner
            auction_result = AuctionResult(
                auction_id=auction.id,
                winner_id=None,  # No winner
                winning_bid=0.0,  # No winning bid
                ended_at=datetime.now()
            )
            db.session.add(auction_result)
    
    try:
        db.session.commit()
        return len(ended_auctions)
    except Exception as e:
        db.session.rollback()
        print(f"Error processing auction results: {e}")
        return 0
