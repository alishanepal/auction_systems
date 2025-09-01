#!/usr/bin/env python3
"""
Test script to demonstrate the Proxy Bidding System functionality
"""

from app import create_app
from app.models import db, User, Product, Auction, Bid, BidderMinimumAmount
from app.proxy_bidding import ProxyBiddingSystem
from datetime import datetime, timedelta
import time

def test_proxy_bidding_system():
    """Test the proxy bidding system functionality"""
    
    app = create_app()
    with app.app_context():
        
        print("=== Testing Proxy Bidding System ===\n")
        
        # Get some existing data for testing
        users = User.query.limit(4).all()
        products = Product.query.limit(2).all()
        
        if len(users) < 4 or len(products) < 2:
            print("Need at least 4 users and 2 products in the database for testing")
            return
        
        bidder1 = users[0]  # First bidder
        bidder2 = users[1]  # Second bidder
        bidder3 = users[2]  # Third bidder
        seller = users[3]   # Seller
        product = products[0]  # First product
        
        print(f"Using bidder1: {bidder1.username}")
        print(f"Using bidder2: {bidder2.username}")
        print(f"Using bidder3: {bidder3.username}")
        print(f"Using seller: {seller.username}")
        print(f"Using product: {product.name}\n")
        
        # Create a test auction that starts in 1 minute and runs for 10 minutes
        start_time = datetime.now() + timedelta(minutes=1)
        end_time = start_time + timedelta(minutes=10)
        
        auction = Auction(
            product_id=product.id,
            start_date=start_time,
            end_date=end_time,
            type='auction'
        )
        db.session.add(auction)
        db.session.commit()
        
        print(f"Created test auction: {auction.id}")
        print(f"Start time: {start_time}")
        print(f"End time: {end_time}\n")
        
        # Test 1: Set proxy bids for upcoming auction
        print("1. Setting proxy bids for upcoming auction...")
        
        # Bidder1 sets proxy bid of 500
        result1 = ProxyBiddingSystem.set_proxy_bid(
            bidder_id=bidder1.id,
            auction_id=auction.id,
            product_id=product.id,
            max_amount=500.0
        )
        print(f"   Bidder1 proxy bid (500): {result1['success']} - {result1['message']}")
        
        # Bidder2 sets proxy bid of 300
        result2 = ProxyBiddingSystem.set_proxy_bid(
            bidder_id=bidder2.id,
            auction_id=auction.id,
            product_id=product.id,
            max_amount=300.0
        )
        print(f"   Bidder2 proxy bid (300): {result2['success']} - {result2['message']}")
        
        # Bidder3 sets proxy bid of 800
        result3 = ProxyBiddingSystem.set_proxy_bid(
            bidder_id=bidder3.id,
            auction_id=auction.id,
            product_id=product.id,
            max_amount=800.0
        )
        print(f"   Bidder3 proxy bid (800): {result3['success']} - {result3['message']}\n")
        
        # Test 2: Get proxy bid status
        print("2. Getting proxy bid status...")
        status1 = ProxyBiddingSystem.get_proxy_bid_status(bidder1.id, auction.id)
        print(f"   Bidder1 status: {status1}")
        
        status2 = ProxyBiddingSystem.get_proxy_bid_status(bidder2.id, auction.id)
        print(f"   Bidder2 status: {status2}")
        
        status3 = ProxyBiddingSystem.get_proxy_bid_status(bidder3.id, auction.id)
        print(f"   Bidder3 status: {status3}\n")
        
        # Test 3: Simulate auction going live
        print("3. Simulating auction going live...")
        
        # Update auction start time to now
        auction.start_date = datetime.now()
        db.session.commit()
        
        print(f"   Auction status: {auction.status}")
        
        # Process proxy bids for live auction
        executed_bids = ProxyBiddingSystem.process_proxy_bids_for_auction(auction.id)
        print(f"   Executed {len(executed_bids)} proxy bids")
        
        for bid in executed_bids:
            print(f"   - Bidder {bid['bidder_id']}: {bid['bid_amount']} - {bid['message']}")
        print()
        
        # Test 4: Check current auction state
        print("4. Checking current auction state...")
        current_bids = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.bid_amount.desc()).all()
        print(f"   Total bids placed: {len(current_bids)}")
        
        for bid in current_bids:
            bidder = User.query.get(bid.bidder_id)
            print(f"   - {bidder.username}: {bid.bid_amount}")
        print()
        
        # Test 5: Simulate manual bid that triggers proxy bids
        print("5. Simulating manual bid that triggers proxy bids...")
        
        # Create a new bidder (bidder4) and place a manual bid
        bidder4 = users[3] if len(users) > 3 else users[0]
        
        # Place a manual bid
        manual_bid = Bid(
            auction_id=auction.id,
            bidder_id=bidder4.id,
            bid_amount=400.0
        )
        db.session.add(manual_bid)
        db.session.commit()
        
        print(f"   Manual bid placed: {bidder4.username} bid 400")
        
        # Process proxy bids again
        executed_bids = ProxyBiddingSystem.process_proxy_bids_for_auction(auction.id)
        print(f"   Executed {len(executed_bids)} proxy bids after manual bid")
        
        for bid in executed_bids:
            print(f"   - Bidder {bid['bidder_id']}: {bid['bid_amount']} - {bid['message']}")
        print()
        
        # Test 6: Update proxy bid
        print("6. Updating proxy bid...")
        
        # Update bidder1's proxy bid to 600
        result_update = ProxyBiddingSystem.set_proxy_bid(
            bidder_id=bidder1.id,
            auction_id=auction.id,
            product_id=product.id,
            max_amount=600.0
        )
        print(f"   Updated bidder1 proxy bid (600): {result_update['success']} - {result_update['message']}")
        
        # Process proxy bids again
        executed_bids = ProxyBiddingSystem.process_proxy_bids_for_auction(auction.id)
        print(f"   Executed {len(executed_bids)} proxy bids after update")
        print()
        
        # Test 7: Get all proxy bids for a user
        print("7. Getting all proxy bids for bidder1...")
        all_proxy_bids = ProxyBiddingSystem.get_all_proxy_bids_for_user(bidder1.id)
        print(f"   Found {len(all_proxy_bids)} proxy bids for bidder1")
        
        for proxy_bid in all_proxy_bids:
            print(f"   - Auction {proxy_bid['auction_id']}: {proxy_bid['proxy_amount']} (Status: {proxy_bid['auction_status']})")
        print()
        
        # Test 8: Remove proxy bid
        print("8. Removing proxy bid...")
        
        # Remove bidder2's proxy bid
        remove_result = ProxyBiddingSystem.remove_proxy_bid(bidder2.id, auction.id)
        print(f"   Remove bidder2 proxy bid: {remove_result['success']} - {remove_result['message']}")
        
        # Check if it's removed
        status_after_remove = ProxyBiddingSystem.get_proxy_bid_status(bidder2.id, auction.id)
        print(f"   Bidder2 status after removal: {status_after_remove['has_proxy']}")
        print()
        
        # Test 9: Final auction state
        print("9. Final auction state...")
        final_bids = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.bid_amount.desc()).all()
        print(f"   Total bids placed: {len(final_bids)}")
        
        for bid in final_bids:
            bidder = User.query.get(bid.bidder_id)
            print(f"   - {bidder.username}: {bid.bid_amount}")
        
        # Get current highest bid
        highest_bid = max(final_bids, key=lambda x: x.bid_amount) if final_bids else None
        if highest_bid:
            winner = User.query.get(highest_bid.bidder_id)
            print(f"   Current winner: {winner.username} with {highest_bid.bid_amount}")
        print()
        
        # Clean up test data
        print("10. Cleaning up test data...")
        Bid.query.filter_by(auction_id=auction.id).delete()
        BidderMinimumAmount.query.filter_by(auction_id=auction.id).delete()
        db.session.delete(auction)
        db.session.commit()
        print("   Test data cleaned up successfully!")
        
        print("\n=== Proxy Bidding Test completed successfully! ===")

if __name__ == "__main__":
    test_proxy_bidding_system()

