"""
Enhanced Proxy Bidding System - eBay-style Implementation

This module implements sophisticated proxy bidding that calculates optimal bids
based on second-highest maximum bid among proxy bidders, ensuring fair pricing
and efficient auction dynamics.
"""

from .models import db, Bid, Auction, BidderMinimumAmount, User
from .utils import calculate_minimum_increment, calculate_minimum_bid
from datetime import datetime
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class EnhancedProxyBiddingSystem:
    """Enhanced proxy bidding system implementing eBay-style optimal bidding"""
    
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
            
            # Set or update the proxy bid
            proxy_bid = BidderMinimumAmount.set_minimum_amount(
                bidder_id=bidder_id,
                auction_id=auction_id,
                product_id=product_id,
                minimum_amount=max_amount
            )
            
            # If auction is live, calculate and place optimal bid
            if auction.status == 'live':
                result = EnhancedProxyBiddingSystem._calculate_and_place_optimal_bid(
                    bidder_id, auction_id, max_amount
                )
                if result['success']:
                    return {
                        'success': True,
                        'message': f'Proxy bid set successfully. {result["message"]}',
                        'proxy_amount': max_amount,
                        'optimal_bid': result.get('optimal_bid'),
                        'auction_state': result.get('auction_state')
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
        """Get the current proxy bid for a user on a specific auction"""
        return BidderMinimumAmount.get_minimum_amount(bidder_id, auction_id)
    
    @staticmethod
    def remove_proxy_bid(bidder_id, auction_id):
        """Remove a proxy bid for a user on a specific auction"""
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
        Uses eBay-style optimal bidding strategy
        
        Args:
            auction_id (int): ID of the auction
            
        Returns:
            list: List of proxy bids that were executed
        """
        try:
            auction = Auction.query.get(auction_id)
            if not auction or auction.status != 'live':
                return []
            
            # Get current auction state
            auction_state = EnhancedProxyBiddingSystem._get_auction_state(auction_id)
            
            # Calculate optimal bids for all proxy bidders
            optimal_bids = EnhancedProxyBiddingSystem._calculate_optimal_bids_for_all(auction_id, auction_state)
            
            executed_bids = []
            
            # Place optimal bids for each proxy bidder
            for bidder_id, optimal_bid_info in optimal_bids.items():
                if optimal_bid_info['should_bid']:
                    result = EnhancedProxyBiddingSystem._place_optimal_bid(
                        bidder_id, auction_id, optimal_bid_info['optimal_amount']
                    )
                    
                    if result['success']:
                        executed_bids.append({
                            'bidder_id': bidder_id,
                            'bid_amount': optimal_bid_info['optimal_amount'],
                            'message': f'Optimal proxy bid of {optimal_bid_info["optimal_amount"]} placed',
                            'reasoning': optimal_bid_info['reasoning']
                        })
                        
                        logger.info(f"Optimal proxy bid executed: User {bidder_id} bid {optimal_bid_info['optimal_amount']} on auction {auction_id}")
            
            return executed_bids
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing proxy bids for auction {auction_id}: {e}")
            return []
    
    @staticmethod
    def _get_auction_state(auction_id: int) -> Dict:
        """
        Get current state of the auction including all bids and proxy bids
        
        Args:
            auction_id (int): ID of the auction
            
        Returns:
            dict: Current auction state
        """
        auction = Auction.query.get(auction_id)
        
        # Get current highest bid
        current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
        
        # Get all proxy bids sorted by maximum amount
        proxy_bids = BidderMinimumAmount.query.filter_by(auction_id=auction_id).order_by(
            BidderMinimumAmount.minimum_amount.desc()
        ).all()
        
        # Get all manual bids (non-proxy bids)
        manual_bids = Bid.query.filter_by(auction_id=auction_id).all()
        
        return {
            'auction_id': auction_id,
            'current_highest_bid': current_highest_bid.bid_amount if current_highest_bid else auction.product.starting_bid,
            'current_highest_bidder': current_highest_bid.bidder_id if current_highest_bid else None,
            'proxy_bids': [(pb.bidder_id, pb.minimum_amount) for pb in proxy_bids],
            'manual_bids': [(mb.bidder_id, mb.bid_amount) for mb in manual_bids],
            'starting_bid': auction.product.starting_bid
        }
    
    @staticmethod
    def _calculate_optimal_bids_for_all(auction_id: int, auction_state: Dict) -> Dict[int, Dict]:
        """
        Calculate optimal bids for all proxy bidders using eBay-style strategy
        
        Args:
            auction_id (int): ID of the auction
            auction_state (dict): Current auction state
            
        Returns:
            dict: Optimal bid information for each proxy bidder
        """
        proxy_bids = auction_state['proxy_bids']
        current_highest = auction_state['current_highest_bid']
        current_winner = auction_state['current_highest_bidder']
        
        if not proxy_bids:
            return {}
        
        # Sort proxy bids by maximum amount (highest first)
        sorted_proxy_bids = sorted(proxy_bids, key=lambda x: x[1], reverse=True)
        
        optimal_bids = {}
        
        for bidder_id, max_amount in sorted_proxy_bids:
            optimal_bid_info = EnhancedProxyBiddingSystem._calculate_optimal_bid_for_bidder(
                bidder_id, max_amount, sorted_proxy_bids, current_highest, current_winner
            )
            optimal_bids[bidder_id] = optimal_bid_info
        
        return optimal_bids
    
    @staticmethod
    def _calculate_optimal_bid_for_bidder(
        bidder_id: int, 
        max_amount: float, 
        all_proxy_bids: List[Tuple[int, float]], 
        current_highest: float, 
        current_winner: Optional[int]
    ) -> Dict:
        """
        Calculate optimal bid for a specific proxy bidder
        
        Args:
            bidder_id (int): ID of the bidder
            max_amount (float): Maximum amount the bidder is willing to pay
            all_proxy_bids (list): All proxy bids sorted by max amount
            current_highest (float): Current highest bid
            current_winner (int): Current winning bidder ID
            
        Returns:
            dict: Optimal bid information
        """
        # Find this bidder's position in the sorted list
        bidder_position = None
        for i, (bid_id, amount) in enumerate(all_proxy_bids):
            if bid_id == bidder_id:
                bidder_position = i
                break
        
        if bidder_position is None:
            return {'should_bid': False, 'reasoning': 'Bidder not found in proxy bids'}
        
        # If this bidder is already winning, no need to bid
        if current_winner == bidder_id:
            return {'should_bid': False, 'reasoning': 'Already winning the auction'}
        
        # Find the second-highest maximum among other proxy bidders
        second_highest_max = None
        for i, (other_bidder_id, other_max_amount) in enumerate(all_proxy_bids):
            if other_bidder_id != bidder_id:
                second_highest_max = other_max_amount
                break
        
        # If no other proxy bidders, bid just above current highest
        if second_highest_max is None:
            if max_amount > current_highest:
                optimal_amount = current_highest + 1  # Minimum increment
                if optimal_amount <= max_amount:
                    return {
                        'should_bid': True,
                        'optimal_amount': optimal_amount,
                        'reasoning': f'Only proxy bidder, bidding just above current highest ({current_highest})'
                    }
            return {'should_bid': False, 'reasoning': 'Cannot outbid current highest with max amount'}
        
        # Calculate optimal bid: minimum increment above second-highest max
        if second_highest_max >= max_amount:
            return {'should_bid': False, 'reasoning': f'Second-highest max ({second_highest_max}) exceeds own max ({max_amount})'}
        
        # Optimal bid is just above second-highest maximum
        optimal_amount = second_highest_max + 1
        
        # Ensure we're not bidding below current highest
        if optimal_amount <= current_highest:
            optimal_amount = current_highest + 1
        
        # Ensure we don't exceed our own maximum
        if optimal_amount > max_amount:
            return {'should_bid': False, 'reasoning': f'Optimal bid ({optimal_amount}) exceeds max amount ({max_amount})'}
        
        return {
            'should_bid': True,
            'optimal_amount': optimal_amount,
            'reasoning': f'Bidding just above second-highest max ({second_highest_max})'
        }
    
    @staticmethod
    def _calculate_and_place_optimal_bid(bidder_id: int, auction_id: int, max_amount: float) -> Dict:
        """
        Calculate and place optimal bid for a specific bidder
        
        Args:
            bidder_id (int): ID of the bidder
            auction_id (int): ID of the auction
            max_amount (float): Maximum amount the bidder is willing to pay
            
        Returns:
            dict: Result of the operation
        """
        try:
            auction_state = EnhancedProxyBiddingSystem._get_auction_state(auction_id)
            
            # Get all proxy bids for this auction
            proxy_bids = auction_state['proxy_bids']
            
            # Calculate optimal bid
            optimal_bid_info = EnhancedProxyBiddingSystem._calculate_optimal_bid_for_bidder(
                bidder_id, max_amount, proxy_bids, 
                auction_state['current_highest_bid'], 
                auction_state['current_highest_bidder']
            )
            
            if not optimal_bid_info['should_bid']:
                return {
                    'success': True,
                    'message': f'No optimal bid needed: {optimal_bid_info["reasoning"]}',
                    'auction_state': auction_state
                }
            
            # Place the optimal bid
            result = EnhancedProxyBiddingSystem._place_optimal_bid(
                bidder_id, auction_id, optimal_bid_info['optimal_amount']
            )
            
            if result['success']:
                return {
                    'success': True,
                    'message': f'Optimal bid of {optimal_bid_info["optimal_amount"]} placed: {optimal_bid_info["reasoning"]}',
                    'optimal_bid': optimal_bid_info['optimal_amount'],
                    'auction_state': auction_state
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error calculating and placing optimal bid: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}
    
    @staticmethod
    def _place_optimal_bid(bidder_id: int, auction_id: int, optimal_amount: float) -> Dict:
        """
        Place an optimal bid in the database
        
        Args:
            bidder_id (int): ID of the bidder
            auction_id (int): ID of the auction
            optimal_amount (float): Optimal bid amount
            
        Returns:
            dict: Result of the operation
        """
        try:
            # Create the bid
            new_bid = Bid(
                auction_id=auction_id,
                bidder_id=bidder_id,
                bid_amount=optimal_amount
            )
            
            db.session.add(new_bid)
            db.session.commit()
            
            logger.info(f"Optimal bid placed: User {bidder_id} bid {optimal_amount} on auction {auction_id}")
            
            return {
                'success': True,
                'message': f'Optimal bid of {optimal_amount} placed successfully',
                'bid_amount': optimal_amount
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error placing optimal bid: {e}")
            return {'success': False, 'message': f'Error placing optimal bid: {str(e)}'}
    
    @staticmethod
    def get_enhanced_proxy_bid_status(bidder_id, auction_id):
        """
        Get detailed status of a proxy bid with enhanced information
        
        Args:
            bidder_id (int): ID of the bidder
            auction_id (int): ID of the auction
            
        Returns:
            dict: Enhanced proxy bid status information
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
            
            # Get current auction state
            auction_state = EnhancedProxyBiddingSystem._get_auction_state(auction_id)
            
            # Calculate optimal bid for this bidder
            proxy_bids = auction_state['proxy_bids']
            optimal_bid_info = EnhancedProxyBiddingSystem._calculate_optimal_bid_for_bidder(
                bidder_id, proxy_amount, proxy_bids,
                auction_state['current_highest_bid'],
                auction_state['current_highest_bidder']
            )
            
            # Check if user is currently winning
            is_winning = auction_state['current_highest_bidder'] == bidder_id
            
            return {
                'success': True,
                'has_proxy': True,
                'proxy_amount': proxy_amount,
                'current_highest_bid': auction_state['current_highest_bid'],
                'is_winning': is_winning,
                'optimal_bid_amount': optimal_bid_info.get('optimal_amount'),
                'should_bid': optimal_bid_info.get('should_bid', False),
                'reasoning': optimal_bid_info.get('reasoning', ''),
                'auction_status': auction.status,
                'total_proxy_bidders': len(proxy_bids)
            }
            
        except Exception as e:
            logger.error(f"Error getting enhanced proxy bid status: {e}")
            return {'success': False, 'message': f'Error getting status: {str(e)}'}
    
    @staticmethod
    def get_auction_analysis(auction_id):
        """
        Get comprehensive analysis of auction state including all proxy bids
        
        Args:
            auction_id (int): ID of the auction
            
        Returns:
            dict: Comprehensive auction analysis
        """
        try:
            auction_state = EnhancedProxyBiddingSystem._get_auction_state(auction_id)
            
            # Calculate optimal bids for all proxy bidders
            optimal_bids = EnhancedProxyBiddingSystem._calculate_optimal_bids_for_all(auction_id, auction_state)
            
            # Find second-highest maximum among proxy bidders
            proxy_bids = auction_state['proxy_bids']
            second_highest_max = None
            if len(proxy_bids) >= 2:
                second_highest_max = proxy_bids[1][1]  # Second highest max amount
            
            analysis = {
                'auction_id': auction_id,
                'current_highest_bid': auction_state['current_highest_bid'],
                'current_winner': auction_state['current_highest_bidder'],
                'total_proxy_bidders': len(proxy_bids),
                'total_manual_bids': len(auction_state['manual_bids']),
                'second_highest_proxy_max': second_highest_max,
                'proxy_bid_breakdown': [],
                'optimal_bids': optimal_bids
            }
            
            # Add breakdown for each proxy bidder
            for bidder_id, max_amount in proxy_bids:
                optimal_info = optimal_bids.get(bidder_id, {})
                analysis['proxy_bid_breakdown'].append({
                    'bidder_id': bidder_id,
                    'max_amount': max_amount,
                    'optimal_amount': optimal_info.get('optimal_amount'),
                    'should_bid': optimal_info.get('should_bid', False),
                    'reasoning': optimal_info.get('reasoning', ''),
                    'is_current_winner': auction_state['current_highest_bidder'] == bidder_id
                })
            
            return {
                'success': True,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing auction: {e}")
            return {'success': False, 'message': f'Error analyzing auction: {str(e)}'}

# Keep the old class for backward compatibility
class ProxyBiddingSystem(EnhancedProxyBiddingSystem):
    """Backward compatibility wrapper for the old proxy bidding system"""
    pass
    
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
        Uses priority-based processing to handle multiple bidders fairly
        
        Args:
            auction_id (int): ID of the auction
            
        Returns:
            list: List of proxy bids that were executed
        """
        try:
            auction = Auction.query.get(auction_id)
            if not auction or auction.status != 'live':
                return []
            
            # Get all proxy bids for this auction, sorted by maximum amount (highest first)
            proxy_bids = BidderMinimumAmount.query.filter_by(auction_id=auction_id).order_by(
                BidderMinimumAmount.minimum_amount.desc()
            ).all()
            
            if not proxy_bids:
                return []
            
            executed_bids = []
            current_highest_amount = auction.product.starting_bid
            current_highest_bidder = None
            
            # Get current highest bid to establish baseline
            current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
            if current_highest_bid:
                current_highest_amount = current_highest_bid.bid_amount
                current_highest_bidder = current_highest_bid.bidder_id
            
            # Process proxy bids in priority order (highest max amount first)
            for proxy_bid in proxy_bids:
                # Skip if this bidder already has the highest bid
                if current_highest_bidder == proxy_bid.bidder_id:
                    continue
                
                # Calculate minimum bid needed to become highest bidder
                minimum_bid_needed = calculate_minimum_bid(current_highest_amount)
                
                # Check if this proxy bid can compete
                if proxy_bid.minimum_amount >= minimum_bid_needed:
                    # Determine optimal bid amount
                    # Use minimum bid strategy to stay competitive
                    optimal_bid_amount = minimum_bid_needed
                    
                    # Create the bid
                    new_bid = Bid(
                        auction_id=auction_id,
                        bidder_id=proxy_bid.bidder_id,
                        bid_amount=optimal_bid_amount
                    )
                    
                    db.session.add(new_bid)
                    db.session.commit()
                    
                    # Update tracking variables
                    current_highest_amount = optimal_bid_amount
                    current_highest_bidder = proxy_bid.bidder_id
                    
                    executed_bids.append({
                        'bidder_id': proxy_bid.bidder_id,
                        'bid_amount': optimal_bid_amount,
                        'message': f'Proxy bid of {optimal_bid_amount} placed successfully'
                    })
                    
                    logger.info(f"Priority proxy bid executed: User {proxy_bid.bidder_id} bid {optimal_bid_amount} on auction {auction_id}")
                else:
                    # This proxy bid cannot compete at current level
                    logger.info(f"Proxy bid skipped: User {proxy_bid.bidder_id} max amount ({proxy_bid.minimum_amount}) below required ({minimum_bid_needed})")
            
            return executed_bids
            
        except Exception as e:
            db.session.rollback()
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
    def get_proxy_bid_competition_analysis(auction_id):
        """
        Analyze proxy bid competition for an auction
        
        Args:
            auction_id (int): ID of the auction
            
        Returns:
            dict: Analysis of proxy bid competition
        """
        try:
            auction = Auction.query.get(auction_id)
            if not auction:
                return {'success': False, 'message': 'Auction not found'}
            
            # Get current highest bid
            current_highest_bid = Bid.query.filter_by(auction_id=auction_id).order_by(Bid.bid_amount.desc()).first()
            current_highest_amount = current_highest_bid.bid_amount if current_highest_bid else auction.product.starting_bid
            
            # Get all proxy bids sorted by amount
            proxy_bids = BidderMinimumAmount.query.filter_by(auction_id=auction_id).order_by(
                BidderMinimumAmount.minimum_amount.desc()
            ).all()
            
            # Calculate minimum bid needed
            minimum_bid_needed = calculate_minimum_bid(current_highest_amount)
            
            # Analyze competition
            competition_analysis = {
                'current_highest_bid': current_highest_amount,
                'current_highest_bidder': current_highest_bid.bidder_id if current_highest_bid else None,
                'minimum_bid_needed': minimum_bid_needed,
                'total_proxy_bidders': len(proxy_bids),
                'active_proxy_bidders': 0,
                'proxy_bid_breakdown': []
            }
            
            for proxy_bid in proxy_bids:
                can_compete = proxy_bid.minimum_amount >= minimum_bid_needed
                is_current_winner = current_highest_bid and current_highest_bid.bidder_id == proxy_bid.bidder_id
                
                if can_compete and not is_current_winner:
                    competition_analysis['active_proxy_bidders'] += 1
                
                competition_analysis['proxy_bid_breakdown'].append({
                    'bidder_id': proxy_bid.bidder_id,
                    'max_amount': proxy_bid.minimum_amount,
                    'can_compete': can_compete,
                    'is_current_winner': is_current_winner,
                    'potential_bid': minimum_bid_needed if can_compete and not is_current_winner else None
                })
            
            return {
                'success': True,
                'analysis': competition_analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing proxy bid competition: {e}")
            return {'success': False, 'message': f'Error analyzing competition: {str(e)}'}

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

