#!/usr/bin/env python3
"""
Test script to demonstrate the BidderMinimumAmount table functionality
"""

from app import create_app
from app.models import db, User, Product, Auction, BidderMinimumAmount
from datetime import datetime, timedelta

def test_bidder_minimum_amount():
    """Test the BidderMinimumAmount table functionality"""
    
    app = create_app()
    with app.app_context():
        
        print("=== Testing BidderMinimumAmount Table ===\n")
        
        # Get some existing data for testing
        users = User.query.limit(3).all()
        products = Product.query.limit(2).all()
        
        if not users or not products:
            print("Need at least 3 users and 2 products in the database for testing")
            return
        
        bidder = users[0]  # First user as bidder
        seller = users[1]  # Second user as seller
        product = products[0]  # First product
        
        print(f"Using bidder: {bidder.username}")
        print(f"Using seller: {seller.username}")
        print(f"Using product: {product.name}\n")
        
        # Create a test auction
        auction = Auction(
            product_id=product.id,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            type='auction'
        )
        db.session.add(auction)
        db.session.commit()
        
        print(f"Created test auction: {auction.id}\n")
        
        # Test 1: Set minimum amount for a bidder
        print("1. Setting minimum amount for bidder...")
        minimum_amount = 150.0
        result = BidderMinimumAmount.set_minimum_amount(
            bidder_id=bidder.id,
            auction_id=auction.id,
            product_id=product.id,
            minimum_amount=minimum_amount
        )
        print(f"   Set minimum amount: ${minimum_amount}")
        print(f"   Record ID: {result.id}")
        print(f"   Created at: {result.created_at}\n")
        
        # Test 2: Get minimum amount
        print("2. Retrieving minimum amount...")
        retrieved_amount = BidderMinimumAmount.get_minimum_amount(bidder.id, auction.id)
        print(f"   Retrieved amount: ${retrieved_amount}\n")
        
        # Test 3: Update minimum amount
        print("3. Updating minimum amount...")
        new_amount = 200.0
        updated_result = BidderMinimumAmount.set_minimum_amount(
            bidder_id=bidder.id,
            auction_id=auction.id,
            product_id=product.id,
            minimum_amount=new_amount
        )
        print(f"   Updated amount: ${new_amount}")
        print(f"   Updated at: {updated_result.updated_at}\n")
        
        # Test 4: Get all minimums for this bidder
        print("4. Getting all minimums for this bidder...")
        bidder_minimums = BidderMinimumAmount.get_bidder_minimums(bidder.id)
        print(f"   Found {len(bidder_minimums)} minimum amount records")
        for minimum in bidder_minimums:
            print(f"   - Auction {minimum.auction_id}: ${minimum.minimum_amount}")
        print()
        
        # Test 5: Get all minimums for this auction
        print("5. Getting all minimums for this auction...")
        auction_minimums = BidderMinimumAmount.get_auction_minimums(auction.id)
        print(f"   Found {len(auction_minimums)} minimum amount records")
        for minimum in auction_minimums:
            print(f"   - Bidder {minimum.bidder.username}: ${minimum.minimum_amount}")
        print()
        
        # Test 6: Test relationships
        print("6. Testing relationships...")
        first_record = BidderMinimumAmount.query.first()
        if first_record:
            print(f"   Bidder: {first_record.bidder.username}")
            print(f"   Product: {first_record.product.name}")
            print(f"   Seller: {first_record.seller.username}")
            print(f"   Auction ID: {first_record.auction_id}")
        print()
        
        # Clean up test data
        print("7. Cleaning up test data...")
        BidderMinimumAmount.query.filter_by(auction_id=auction.id).delete()
        db.session.delete(auction)
        db.session.commit()
        print("   Test data cleaned up successfully!")
        
        print("\n=== Test completed successfully! ===")

if __name__ == "__main__":
    test_bidder_minimum_amount()

