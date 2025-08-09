from flask import request
from flask_socketio import emit, join_room
from . import socketio
from .models import db, Auction, Product
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
        
        # Store current status for next comparison
        setattr(db.session, prev_status_attr, current_status)
    
    # Broadcast updates if any
    if updated_auctions:
        # Broadcast updates to all clients
        socketio.emit('auctions_updated', {'auctions': updated_auctions})

# Background task for periodic status updates
def background_task():
    """Background task to periodically update auction statuses"""
    while True:
        # Update auction statuses every 60 seconds
        update_auction_statuses()
        time.sleep(60)

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