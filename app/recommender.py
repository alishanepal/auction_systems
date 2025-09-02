from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import current_app
from .models import db, Product, Bid, BidHistory, Auction, User
from sqlalchemy import func
from datetime import datetime

def build_product_matrix(products):
    """Build TF-IDF matrix from product details with enhanced text processing"""
    texts = []
    for p in products:
        # Combine relevant text fields with weighted repetition for important fields
        content_parts = []
        content_parts.extend([p.name] * 3)  # Product name gets highest weight
        if p.description:
            content_parts.extend([p.description] * 2)
        if p.keywords:
            content_parts.extend([p.keywords] * 2)
        if p.category:
            content_parts.append(p.category.name)
        if p.subcategory:
            content_parts.append(p.subcategory.name)
        content = " ".join(content_parts)
        texts.append(content.lower())
    
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=5000,
        ngram_range=(1, 2)
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        return tfidf_matrix, vectorizer
    except Exception as e:
        current_app.logger.error(f"Error building TF-IDF matrix: {str(e)}")
        return None, None



def get_recommended_products(user_id, limit=10):
    """Get personalized product recommendations with enhanced scoring"""
    if not user_id:
        return [], {}

    current_time = datetime.now()
    available_auctions = (
        Auction.query
        .filter(
            # Only include live and upcoming auctions (not ended ones)
            (Auction.start_date <= current_time) & (Auction.end_date > current_time) |  # Live auctions
            (Auction.start_date > current_time)  # Upcoming auctions
        )
        .all()
    )
    
    if not available_auctions:
        return [], {}

    products = [auction.product for auction in available_auctions]
    bid_history = BidHistory.query.filter_by(user_id=user_id).all()
    if not bid_history:
        return [], {}

    user_bid_products = []
    bid_counts = {}
    category_counts = defaultdict(int)
    subcategory_counts = defaultdict(int)
    
    for entry in bid_history:
        product = db.session.query(Product).get(entry.product_id)
        if product:
            user_bid_products.append(product)
            bid_counts[product.id] = entry.bid_count or 1
            if product.category_id:
                category_counts[product.category_id] += entry.bid_count or 1
            if product.subcategory_id:
                subcategory_counts[product.subcategory_id] += entry.bid_count or 1

    if not user_bid_products:
        return [], {}

    tfidf_matrix, vectorizer = build_product_matrix(products)
    if tfidf_matrix is None:
        return [], {}

    cosine_sim_matrix = cosine_similarity(tfidf_matrix)
    product_index = {p.id: idx for idx, p in enumerate(products)}
    product_scores = defaultdict(float)
    score_details = {}

    max_bid_count = max(bid_counts.values()) if bid_counts else 1
    max_category_count = max(category_counts.values()) if category_counts else 1
    max_subcategory_count = max(subcategory_counts.values()) if subcategory_counts else 1

    # Enhanced scoring weights (α, β, γ from the formula)
    ALPHA = 0.45  # Cosine similarity weight
    BETA = 0.30   # Past bid score weight  
    GAMMA = 0.25  # Category/subcategory score weight

    for past_product in user_bid_products:
        if past_product.id not in product_index:
            continue

        past_idx = product_index[past_product.id]
        sim_scores = list(enumerate(cosine_sim_matrix[past_idx]))
        bid_count_factor = bid_counts.get(past_product.id, 1) / max_bid_count

        for idx, similarity in sim_scores:
            candidate = products[idx]
            if candidate.id == past_product.id:
                continue

            # 1. Content Similarity Score (α * CosineSimilarity)
            content_score = similarity * ALPHA

            # 2. Past Bid Score (β * PastBidScore)
            past_bid_score = 0.0
            if candidate.id in bid_counts:
                past_bid_score = (bid_counts[candidate.id] / max_bid_count) * BETA
            elif candidate.category_id == past_product.category_id:
                # Bonus for same category
                past_bid_score = (category_counts.get(candidate.category_id, 0) / max_category_count) * BETA * 0.5

            # 3. Category/Subcategory Score (γ * CategoryScore)
            category_score = 0.0
            subcategory_score = 0.0
            
            if candidate.category_id == past_product.category_id:
                category_score = (category_counts[candidate.category_id] / max_category_count) * GAMMA * 0.6
            
            if candidate.subcategory_id == past_product.subcategory_id:
                subcategory_score = (subcategory_counts[candidate.subcategory_id] / max_subcategory_count) * GAMMA * 0.4

            # 4. Price Similarity (bonus factor)
            price_diff = abs(candidate.starting_bid - past_product.starting_bid)
            price_factor = 1.0 / (1.0 + price_diff / max(1, past_product.starting_bid))
            price_score = price_factor * 0.10

            # 5. Final Score Calculation
            final_score = (
                content_score + 
                past_bid_score + 
                category_score + 
                subcategory_score + 
                price_score
            )

            # Apply bid count multiplier
            final_score *= (1.0 + bid_count_factor)
            product_scores[candidate.id] += final_score

            if candidate.id not in score_details or final_score > score_details[candidate.id]["final_score"]:
                score_details[candidate.id] = {
                    "content_similarity": round(content_score, 3),
                    "past_bid_score": round(past_bid_score, 3),
                    "category_score": round(category_score, 3),
                    "subcategory_score": round(subcategory_score, 3),
                    "price_similarity": round(price_score, 3),
                    "bid_weight": round(bid_count_factor, 3),
                    "final_score": round(final_score, 3)
                }

    recommended_ids = sorted(product_scores.keys(), key=lambda k: product_scores[k], reverse=True)
    recommended_products = [
        p for p in products 
        if p.id in recommended_ids and p.id in score_details
    ][:limit]

    return recommended_products, score_details

def sort_products_for_user(products, user_id, limit=None):
    """Sort products based on user preferences with enhanced scoring"""
    if not user_id or not products:
        return products[:limit] if limit else products

    bid_history = BidHistory.query.filter_by(user_id=user_id).all()
    if not bid_history:
        return products[:limit] if limit else products

    tfidf_matrix, vectorizer = build_product_matrix(products)
    if tfidf_matrix is None:
        return products[:limit] if limit else products

    cosine_sim_matrix = cosine_similarity(tfidf_matrix)
    product_index = {p.id: idx for idx, p in enumerate(products)}
    product_scores = defaultdict(float)

    user_bid_products = []
    bid_counts = {}
    category_counts = defaultdict(int)
    subcategory_counts = defaultdict(int)
    
    for entry in bid_history:
        product = Product.query.get(entry.product_id)
        if product:
            user_bid_products.append(product)
            bid_counts[product.id] = entry.bid_count or 1
            if product.category_id:
                category_counts[product.category_id] += entry.bid_count or 1
            if product.subcategory_id:
                subcategory_counts[product.subcategory_id] += entry.bid_count or 1

    max_bid_count = max(bid_counts.values()) if bid_counts else 1
    max_category_count = max(category_counts.values()) if category_counts else 1
    max_subcategory_count = max(subcategory_counts.values()) if subcategory_counts else 1

    for past_product in user_bid_products:
        if past_product.id not in product_index:
            continue

        past_idx = product_index[past_product.id]
        sim_scores = list(enumerate(cosine_sim_matrix[past_idx]))
        bid_count_factor = bid_counts.get(past_product.id, 1) / max_bid_count

        for idx, similarity in sim_scores:
            candidate = products[idx]
            if candidate.id == past_product.id:
                continue

            # Enhanced scoring for sorting
            content_score = similarity * 0.5
            
            category_bonus = 0.0
            if candidate.category_id == past_product.category_id:
                category_bonus = (category_counts[candidate.category_id] / max_category_count) * 0.3
            
            subcategory_bonus = 0.0
            if candidate.subcategory_id == past_product.subcategory_id:
                subcategory_bonus = (subcategory_counts[candidate.subcategory_id] / max_subcategory_count) * 0.2

            score = (content_score + category_bonus + subcategory_bonus) * (1.0 + bid_count_factor)
            product_scores[candidate.id] += score

    sorted_products = sorted(
        products,
        key=lambda p: product_scores.get(p.id, 0.0),
        reverse=True
    )

    return sorted_products[:limit] if limit else sorted_products

def get_category_based_recommendations(user_id, limit=10):
    """Get recommendations based on user's preferred categories"""
    if not user_id:
        return [], {}
    
    # Get user's preferred categories based on bid history
    category_preferences = (
        db.session.query(
            BidHistory.category_id,
            func.count(BidHistory.id).label('bid_count')
        )
        .filter(BidHistory.user_id == user_id)
        .group_by(BidHistory.category_id)
        .order_by(func.count(BidHistory.id).desc())
        .limit(5)
        .all()
    )
    
    if not category_preferences:
        return [], {}
    
    preferred_category_ids = [cat.category_id for cat in category_preferences]
    
    # Get products from preferred categories
    current_time = datetime.now()
    category_products = (
        db.session.query(Product)
        .join(Auction, Auction.product_id == Product.id)
        .filter(
            Product.category_id.in_(preferred_category_ids),
            # Only include live and upcoming auctions (not ended ones)
            (Auction.start_date <= current_time) & (Auction.end_date > current_time) |  # Live auctions
            (Auction.start_date > current_time)  # Upcoming auctions
        )
        .all()
    )
    
    # Score products based on category preference strength
    product_scores = {}
    for product in category_products:
        category_bid_count = next(
            (cat.bid_count for cat in category_preferences if cat.category_id == product.category_id),
            0
        )
        product_scores[product.id] = category_bid_count
    
    # Sort by score and return top products
    sorted_products = sorted(
        category_products,
        key=lambda p: product_scores[p.id],
        reverse=True
    )[:limit]
    
    score_details = {
        p.id: {"category_score": product_scores[p.id]} 
        for p in sorted_products
    }
    
    return sorted_products, score_details

def update_bid_history(user_id, product_id, auction_id, bid_amount):
    """Update bid history when a user places a bid"""
    product = Product.query.get(product_id)
    if not product:
        current_app.logger.error(f"Product {product_id} not found")
        return

    try:
        # Get or create bid history entry
        history = BidHistory.query.filter_by(
            user_id=user_id,
            product_id=product_id
        ).first()

        if history:
            history.bid_count = (history.bid_count or 0) + 1
            history.last_bid_time = func.now()
        else:
            history = BidHistory(
                user_id=user_id,
                product_id=product_id,
                category_id=product.category_id,
                subcategory_id=product.subcategory_id,
                seller_id=product.seller_id,
                bid_count=1,
                last_bid_time=func.now()
            )
            db.session.add(history)

        db.session.commit()
        current_app.logger.debug(f"Updated bid history for user {user_id} on product {product_id}")

    except Exception as e:
        current_app.logger.error(f"Error updating bid history: {str(e)}")
        db.session.rollback()
