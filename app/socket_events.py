from flask import request
from flask_socketio import emit, join_room
from . import socketio
from .models import db, Auction, Product, AuctionResult, Bid
from .proxy_bidding import ProxyBiddingSystem
from datetime import datetime
import threading
import time

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_auction')
def handle_join_auction(data):
    """Handle client joining an auction room"""
    auction_id = data.get('auction_id')
    if auction_id:
        # Join the room for this auction
        join_room(f'auction_{auction_id}')
        emit('status', {'msg': f'Joined auction {auction_id}'})

@socketio.on('request_status_update')
def handle_status_update_request():
    """Send status updates for all auctions"""
    update_auction_statuses()
    emit('status_updated', {'msg': 'Auction statuses updated'})

def update_auction_statuses():
    """Update auction statuses based on current time"""
    # Get all auctions
    auctions = Auction.query.all()
    
    updated_auctions = []
    
    # Check for status changes
    for auction in auctions:
        # Get current status
        current_status = auction.status
        
        # Store the auction's previous status in a session attribute if it exists
        prev_status_attr = f'_prev_status_{auction.id}'
        prev_status = getattr(db.session, prev_status_attr, None)
        
        # If we have a previous status and it's different from current, add to updated list
        if prev_status is not None and prev_status != current_status:
            updated_auctions.append({
                'id': auction.id,
                'status': current_status,
                'product_name': auction.product.name
            })
            
            # If auction just went live, process proxy bids
            if current_status == 'live' and prev_status == 'upcoming':
                process_proxy_bids_for_live_auction(auction)
            
            # If auction just ended, process the results
            if current_status == 'ended' and prev_status == 'live':
                process_auction_result(auction)
        
        # Store current status for next comparison
        setattr(db.session, prev_status_attr, current_status)
    
    # Broadcast updates if any
    if updated_auctions:
        # Broadcast updates to all clients
        socketio.emit('auctions_updated', {'auctions': updated_auctions})

def process_proxy_bids_for_live_auction(auction):
    """Process proxy bids when an auction goes live"""
    try:
        print(f"Processing proxy bids for auction {auction.id} that just went live")
        
        # Get all proxy bids for this auction
        proxy_bids = ProxyBiddingSystem.process_proxy_bids_for_auction(auction.id)
        
        if proxy_bids:
            print(f"Executed {len(proxy_bids)} proxy bids for auction {auction.id}")
            
            # Broadcast proxy bid executions to auction room
            socketio.emit('proxy_bids_executed', {
                'auction_id': auction.id,
                'proxy_bids': proxy_bids
            }, room=f'auction_{auction.id}')
        
    except Exception as e:
        print(f"Error processing proxy bids for live auction {auction.id}: {e}")

def process_auction_result(auction):
    """Process auction result for a specific auction"""
    try:
        # Check if result already exists
        existing_result = AuctionResult.query.filter_by(auction_id=auction.id).first()
        if existing_result:
            return
        
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
                
                # Broadcast winner announcement
                socketio.emit('auction_ended', {
                    'auction_id': auction.id,
                    'product_name': auction.product.name,
                    'winner': highest_bid.bidder.username,
                    'winning_bid': highest_bid.bid_amount,
                    'has_winner': True
                })
            else:
                # Reserve price not met - no winner
                auction_result = AuctionResult(
                    auction_id=auction.id,
                    winner_id=None,
                    winning_bid=highest_bid.bid_amount,  # Store the actual highest bid amount
                    ended_at=datetime.now()
                )
                db.session.add(auction_result)
                
                # Broadcast no winner announcement
                socketio.emit('auction_ended', {
                    'auction_id': auction.id,
                    'product_name': auction.product.name,
                    'has_winner': False,
                    'reason': 'Reserve price not met'
                })
        else:
            # No bids placed - no winner
            auction_result = AuctionResult(
                auction_id=auction.id,
                winner_id=None,
                winning_bid=0.0,
                ended_at=datetime.now()
            )
            db.session.add(auction_result)
            
            # Broadcast no winner announcement
            socketio.emit('auction_ended', {
                'auction_id': auction.id,
                'product_name': auction.product.name,
                'has_winner': False,
                'reason': 'No bids placed'
            })
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"Error processing auction result for auction {auction.id}: {e}")

# Background task for periodic status updates
def background_task():
    """Background task to periodically update auction statuses"""
    from app import create_app
    app = create_app()
    
    with app.app_context():
        while True:
            try:
                # Update auction statuses every 60 seconds
                update_auction_statuses()
                time.sleep(60)
            except Exception as e:
                print(f"Error in background task: {e}")
                time.sleep(60)  # Continue even if there's an error

# Start the background task when the server starts
background_thread = None

@socketio.on('connect')
def start_background_task():
    """Start background task for periodic status updates if not already running"""
    global background_thread
    
    # Start the background task if it's not already running
    if background_thread is None or not background_thread.is_alive():
        background_thread = threading.Thread(target=background_task)
        background_thread.daemon = True  # Daemon thread will be killed when the main thread exits
        background_thread.start()
        print("Background task started for auction status updates")
    
    # Also update statuses immediately on connect
    update_auction_statuses()