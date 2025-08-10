from .models import db, Product, Category, Subcategory, User, SearchHistory, BidHistory, Auction
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import re

def get_user_preferences(user_id):
    """Get user preferences based on search and bid history"""
    preferences = {
        'categories': defaultdict(int),
        'subcategories': defaultdict(int),
        'sellers': defaultdict(int),
        'keywords': defaultdict(int),
        'price_range': {'min': float('inf'), 'max': 0}
    }
    
    # Get search history preferences
    search_history = db.session.query(SearchHistory).filter_by(user_id=user_id).all()
    for search in search_history:
        # Extract keywords from search queries
        words = re.findall(r'\b\w+\b', search.query.lower())
        for word in words:
            if len(word) > 2:  # Only consider words longer than 2 characters
                preferences['keywords'][word] += 1
    
    # Get bid history preferences
    bid_history = db.session.query(BidHistory).filter_by(user_id=user_id).all()
    for bid in bid_history:
        # Get product details through the auction relationship
        auction = db.session.query(Auction).get(bid.auction_id) if bid.auction_id else None
        product = db.session.query(Product).get(bid.product_id) if bid.product_id else None
        
        if product and product.category:
            # Category preference
            preferences['categories'][product.category.name] += 1
            
            # Subcategory preference
            if product.subcategory:
                preferences['subcategories'][product.subcategory.name] += 1
        
        # Seller preference
        if product and product.seller:
            preferences['sellers'][product.seller.username] += 1
        
        # Price range
        if bid.bid_amount:
            preferences['price_range']['min'] = min(preferences['price_range']['min'], bid.bid_amount)
            preferences['price_range']['max'] = max(preferences['price_range']['max'], bid.bid_amount)
    
    return preferences

def create_product_vector(product, user_preferences):
    """Create a feature vector for a product based on user preferences"""
    features = []
    
    # Category feature
    if product.category:
        category_weight = user_preferences['categories'].get(product.category.name, 0)
        features.extend([category_weight] * 3)  # Give more weight to category
    else:
        features.extend([0] * 3)
    
    # Subcategory feature
    if product.subcategory:
        subcategory_weight = user_preferences['subcategories'].get(product.subcategory.name, 0)
        features.extend([subcategory_weight] * 2)  # Give weight to subcategory
    else:
        features.extend([0] * 2)
    
    # Seller feature
    if product.seller:
        seller_weight = user_preferences['sellers'].get(product.seller.username, 0)
        features.extend([seller_weight] * 2)  # Give weight to seller
    else:
        features.extend([0] * 2)
    
    # Price feature (normalized)
    price = product.starting_bid
    if user_preferences['price_range']['max'] > user_preferences['price_range']['min']:
        normalized_price = (price - user_preferences['price_range']['min']) / \
                          (user_preferences['price_range']['max'] - user_preferences['price_range']['min'])
        features.append(normalized_price)
    else:
        features.append(0.5)  # Default to middle if no price range
    
    # Keywords feature
    if product.keywords:
        keyword_score = 0
        product_keywords = re.findall(r'\b\w+\b', product.keywords.lower())
        for keyword in product_keywords:
            keyword_score += user_preferences['keywords'].get(keyword, 0)
        features.append(keyword_score)
    else:
        features.append(0)
    
    # Description keywords feature
    if product.description:
        desc_score = 0
        desc_keywords = re.findall(r'\b\w+\b', product.description.lower())
        for keyword in desc_keywords:
            desc_score += user_preferences['keywords'].get(keyword, 0)
        features.append(desc_score)
    else:
        features.append(0)
    
    return np.array(features)

def get_recommended_products(user_id, limit=12):
    """Get personalized product recommendations for a user"""
    if not user_id:
        # If no user, return recent live auctions
        live_auctions = db.session.query(Auction).filter(
            Auction.start_date <= func.now(),
            Auction.end_date > func.now()
        ).order_by(desc(Auction.created_at)).limit(limit).all()
        return [auction.product for auction in live_auctions]
    
    # Get user preferences
    user_preferences = get_user_preferences(user_id)
    
    # If user has no history, return recent live auctions
    if not any(user_preferences['categories'].values()) and not any(user_preferences['keywords'].values()):
        live_auctions = db.session.query(Auction).filter(
            Auction.start_date <= func.now(),
            Auction.end_date > func.now()
        ).order_by(desc(Auction.created_at)).limit(limit).all()
        return [auction.product for auction in live_auctions]
    
    # Get all live auction products
    live_auctions = db.session.query(Auction).filter(
        Auction.start_date <= func.now(),
        Auction.end_date > func.now()
    ).all()
    
    products = [auction.product for auction in live_auctions]
    
    if not products:
        return []
    
    # Create feature vectors for all products
    product_vectors = []
    for product in products:
        vector = create_product_vector(product, user_preferences)
        product_vectors.append(vector)
    
    # Create user preference vector (ideal vector)
    user_vector = create_user_preference_vector(user_preferences)
    
    # Calculate cosine similarities
    similarities = []
    for i, product_vector in enumerate(product_vectors):
        if np.linalg.norm(product_vector) > 0 and np.linalg.norm(user_vector) > 0:
            similarity = np.dot(product_vector, user_vector) / (np.linalg.norm(product_vector) * np.linalg.norm(user_vector))
        else:
            similarity = 0
        similarities.append((similarity, products[i]))
    
    # Sort by similarity and return top products
    similarities.sort(key=lambda x: x[0], reverse=True)
    recommended_products = [product for similarity, product in similarities[:limit]]
    
    return recommended_products

def create_user_preference_vector(user_preferences):
    """Create an ideal user preference vector"""
    # This represents the "perfect" product for the user
    features = []
    
    # Category preference (use the most preferred category)
    if user_preferences['categories']:
        max_category_weight = max(user_preferences['categories'].values())
        features.extend([max_category_weight] * 3)
    else:
        features.extend([0] * 3)
    
    # Subcategory preference
    if user_preferences['subcategories']:
        max_subcategory_weight = max(user_preferences['subcategories'].values())
        features.extend([max_subcategory_weight] * 2)
    else:
        features.extend([0] * 2)
    
    # Seller preference
    if user_preferences['sellers']:
        max_seller_weight = max(user_preferences['sellers'].values())
        features.extend([max_seller_weight] * 2)
    else:
        features.extend([0] * 2)
    
    # Price preference (prefer middle of user's price range)
    if user_preferences['price_range']['max'] > user_preferences['price_range']['min']:
        preferred_price = (user_preferences['price_range']['min'] + user_preferences['price_range']['max']) / 2
        normalized_price = (preferred_price - user_preferences['price_range']['min']) / \
                          (user_preferences['price_range']['max'] - user_preferences['price_range']['min'])
        features.append(normalized_price)
    else:
        features.append(0.5)
    
    # Keywords preference (use the most common keywords)
    if user_preferences['keywords']:
        max_keyword_weight = max(user_preferences['keywords'].values())
        features.append(max_keyword_weight)
    else:
        features.append(0)
    
    # Description keywords preference
    if user_preferences['keywords']:
        max_keyword_weight = max(user_preferences['keywords'].values())
        features.append(max_keyword_weight)
    else:
        features.append(0)
    
    return np.array(features)

def update_bid_history(user_id, product_id, auction_id, bid_amount):
    """Update bid history when a user places a bid"""
    from .models import db
    
    # Get product details
    product = db.session.query(Product).get(product_id)
    if not product:
        return
    
    # Create new bid history record
    new_history = BidHistory(
        user_id=user_id,
        product_id=product_id,
        auction_id=auction_id,
        bid_amount=bid_amount,
        timestamp=func.now()
    )
    db.session.add(new_history)
    db.session.commit()
