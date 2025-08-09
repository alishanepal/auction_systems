from app import create_app
from app.models import db, Auction
from datetime import datetime

def update_auction_statuses():
    """Update all existing auction statuses to the new format"""
    app = create_app()
    
    with app.app_context():
        # Get all auctions
        auctions = Auction.query.all()
        now = datetime.utcnow()
        
        # Map old statuses to new ones
        status_updates = {
            'pending': 'upcoming',
            'active': 'live',
            'closed': 'ended'
        }
        
        updated_count = 0
        
        for auction in auctions:
            old_status = auction.status
            
            # Update based on time first
            if now < auction.start_date:
                auction.status = 'upcoming'
            elif now >= auction.start_date and now < auction.end_date:
                auction.status = 'live'
            else:
                auction.status = 'ended'
            
            # If status didn't change based on time but is an old status name, map it
            if auction.status == old_status and old_status in status_updates:
                auction.status = status_updates[old_status]
                
            if auction.status != old_status:
                updated_count += 1
                print(f"Updated auction {auction.id} from '{old_status}' to '{auction.status}'")
        
        # Commit changes
        if updated_count > 0:
            db.session.commit()
            print(f"Successfully updated {updated_count} auctions")
        else:
            print("No auctions needed updating")

if __name__ == '__main__':
    update_auction_statuses()