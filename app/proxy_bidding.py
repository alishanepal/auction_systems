"""
Proxy Bidding System using Greedy Algorithm

This module implements automatic proxy bidding functionality that allows users to set
a maximum bid amount, and the system automatically bids the minimum required amount
to stay ahead of other bidders, up to the user's maximum limit.
"""

from .models import db, Bid, Auction, BidderMinimumAmount, User
from .utils import calculate_minimum_increment, calculate_minimum_bid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProxyBiddingSystem:
    """Proxy bidding system using greedy algorithm"""
    
    @staticmethod
    def set_proxy_bid(bidder_id, auction_id, product_id, max_amount):
        """
        Set or update a proxy bid for a user on a specific auction
        
        Args:
            bidder_id (int): ID of the bidder
            auction_id (int): ID of the auction
            product_id (int): ID of the product
            max_amount (float): Maximum amount the user is willing to bid
            
        Returns:
            dict: Result of the operation
        """
        try:
            # Validate auction exists and is active
            auction = Auction.query.get(auction_id)
            if not auction:
                return {'success': False, 'message': 'Auction not found'}
            
            if auction.status == 'ended':
                return {'success': False, 'message': 'Auction has ended'}
            
            # Get current highest bid
            current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
            current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else auction.product.starting_bid
            
            # Validate max_amount is reasonable
            if max_amount <= current_highest_amount:
                return {
                    'success': False, 
                    'message': f'Maximum amount must be higher than current highest bid ({current_highest_amount})'
                }
            
            # Set or update the proxy bid
            proxy_bid = BidderMinimumAmount.set_minimum_amount(
                bidder_id=bidder_id,
                auction_id=auction_id,
                product_id=product_id,
                minimum_amount=max_amount
            )
            
            # If auction is live, immediately try to place a bid
            if auction.status == 'live':
                result = ProxyBiddingSystem._execute_proxy_bid(bidder_id, auction_id, max_amount)
                if result['success']:
                    return {
                        'success': True,
                        'message': f'Proxy bid set successfully. {result["message"]}',
                        'proxy_amount': max_amount,
                        'current_bid': result.get('current_bid')
                    }
                else:
                    return {
                        'success': True,
                        'message': f'Proxy bid set successfully. {result["message"]}',
                        'proxy_amount': max_amount
                    }
            
            return {
                'success': True,
                'message': f'Proxy bid of {max_amount} set successfully for upcoming auction',
                'proxy_amount': max_amount
            }
            
        except Exception as e:
            logger.error(f"Error setting proxy bid: {e}")
            return {'success': False, 'message': f'Error setting proxy bid: {str(e)}'}
    
    @staticmethod
    def get_proxy_bid(bidder_id, auction_id):
        """
        Get the current proxy bid for a user on a specific auction
        
        Args:
            bidder_id (int): ID of the bidder
            auction_id (int): ID of the auction
            
        Returns:
            float or None: The proxy bid amount, or None if not set
        """
        return BidderMinimumAmount.get_minimum_amount(bidder_id, auction_id)
    
    @staticmethod
    def remove_proxy_bid(bidder_id, auction_id):
        """
        Remove a proxy bid for a user on a specific auction
        
        Args:
            bidder_id (int): ID of the bidder
            auction_id (int): ID of the auction
            
        Returns:
            dict: Result of the operation
        """
        try:
            proxy_bid = BidderMinimumAmount.query.filter_by(
                bidder_id=bidder_id, 
                auction_id=auction_id
            ).first()
            
            if proxy_bid:
                db.session.delete(proxy_bid)
                db.session.commit()
                return {'success': True, 'message': 'Proxy bid removed successfully'}
            else:
                return {'success': False, 'message': 'No proxy bid found'}
                
        except Exception as e:
            logger.error(f"Error removing proxy bid: {e}")
            return {'success': False, 'message': f'Error removing proxy bid: {str(e)}'}
    
    @staticmethod
    def process_proxy_bids_for_auction(auction_id):
        """
        Process all proxy bids for a specific auction when a new bid is placed
        
        Args:
            auction_id (int): ID of the auction
            
        Returns:
            list: List of proxy bids that were executed
        """
        try:
            auction = Auction.query.get(auction_id)
            if not auction or auction.status != 'live':
                return []
            
            # Get all proxy bids for this auction
            proxy_bids = BidderMinimumAmount.query.filter_by(auction_id=auction_id).all()
            
            executed_bids = []
            
            for proxy_bid in proxy_bids:
                result = ProxyBiddingSystem._execute_proxy_bid(
                    proxy_bid.bidder_id, 
                    auction_id, 
                    proxy_bid.minimum_amount
                )
                
                if result['success']:
                    executed_bids.append({
                        'bidder_id': proxy_bid.bidder_id,
                        'bid_amount': result.get('bid_amount'),
                        'message': result['message']
                    })
            
            return executed_bids
            
        except Exception as e:
            logger.error(f"Error processing proxy bids for auction {auction_id}: {e}")
            return []
    
    @staticmethod
    def _execute_proxy_bid(bidder_id, auction_id, max_amount):
        """
        Execute a proxy bid using greedy algorithm
        
        Args:
            bidder_id (int): ID of the bidder
            auction_id (int): ID of the auction
            max_amount (float): Maximum amount the user is willing to bid
            
        Returns:
            dict: Result of the proxy bid execution
        """
        try:
            auction = Auction.query.get(auction_id)
            if not auction or auction.status != 'live':
                return {'success': False, 'message': 'Auction not available for bidding'}
            
            # Get current highest bid
            current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
            current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else auction.product.starting_bid
            
            # Check if current highest bidder is the same user
            if current_highest_bid and current_highest_bid.bidder_id == bidder_id:
                return {'success': False, 'message': 'User already has the highest bid'}
            
            # Calculate the minimum bid needed to become the highest bidder
            minimum_bid_needed = calculate_minimum_bid(current_highest_amount)
            
            # If minimum bid needed exceeds max amount, cannot bid
            if minimum_bid_needed > max_amount:
                return {
                    'success': False, 
                    'message': f'Cannot bid. Minimum required ({minimum_bid_needed}) exceeds maximum amount ({max_amount})'
                }
            
            # Use minimum bid strategy: only bid the minimum amount required
            # This ensures consistency with user preferences for minimum bidding
            optimal_bid_amount = minimum_bid_needed
            
            # Create the bid
            new_bid = Bid(
                auction_id=auction_id,
                bidder_id=bidder_id,
                bid_amount=optimal_bid_amount
            )
            
            db.session.add(new_bid)
            db.session.commit()
            
            logger.info(f"Proxy bid executed: User {bidder_id} bid {optimal_bid_amount} on auction {auction_id}")
            
            return {
                'success': True,
                'message': f'Proxy bid of {optimal_bid_amount} placed successfully',
                'bid_amount': optimal_bid_amount,
                'current_bid': optimal_bid_amount
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error executing proxy bid: {e}")
            return {'success': False, 'message': f'Error executing proxy bid: {str(e)}'}
    
    @staticmethod
    def get_proxy_bid_status(bidder_id, auction_id):
        """
        Get detailed status of a proxy bid
        
        Args:
            bidder_id (int): ID of the bidder
            auction_id (int): ID of the auction
            
        Returns:
            dict: Proxy bid status information
        """
        try:
            auction = Auction.query.get(auction_id)
            if not auction:
                return {'success': False, 'message': 'Auction not found'}
            
            proxy_amount = BidderMinimumAmount.get_minimum_amount(bidder_id, auction_id)
            
            if not proxy_amount:
                return {
                    'success': True,
                    'has_proxy': False,
                    'message': 'No proxy bid set'
                }
            
            # Get current highest bid
            current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
            current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else auction.product.starting_bid
            
            # Check if user is currently winning
            is_winning = current_highest_bid and current_highest_bid.bidder_id == bidder_id
            
            # Calculate remaining budget
            remaining_budget = proxy_amount - current_highest_amount if is_winning else proxy_amount - current_highest_amount
            
            return {
                'success': True,
                'has_proxy': True,
                'proxy_amount': proxy_amount,
                'current_highest_bid': current_highest_amount,
                'is_winning': is_winning,
                'remaining_budget': max(0, remaining_budget),
                'auction_status': auction.status
            }
            
        except Exception as e:
            logger.error(f"Error getting proxy bid status: {e}")
            return {'success': False, 'message': f'Error getting proxy bid status: {str(e)}'}
    
    @staticmethod
    def get_all_proxy_bids_for_user(bidder_id):
        """
        Get all proxy bids for a specific user
        
        Args:
            bidder_id (int): ID of the bidder
            
        Returns:
            list: List of proxy bids with auction information
        """
        try:
            proxy_bids = BidderMinimumAmount.query.filter_by(bidder_id=bidder_id).all()
            
            result = []
            for proxy_bid in proxy_bids:
                auction = proxy_bid.auction
                current_highest_bid = Bid.query.filter_by(auction_id=auction.id).order_by(Bid.bid_amount.desc()).first()
                current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else auction.product.starting_bid
                
                result.append({
                    'auction_id': auction.id,
                    'product_name': proxy_bid.product.name,
                    'proxy_amount': proxy_bid.minimum_amount,
                    'current_highest_bid': current_highest_amount,
                    'auction_status': auction.status,
                    'is_winning': current_highest_bid and current_highest_bid.bidder_id == bidder_id,
                    'created_at': proxy_bid.created_at,
                    'updated_at': proxy_bid.updated_at
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting proxy bids for user {bidder_id}: {e}")
            return []

