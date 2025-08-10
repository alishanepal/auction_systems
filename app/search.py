from flask import Blueprint, render_template, request, jsonify, session
from .models import Product, Category, Subcategory, Auction, User, SearchHistory
from .utils import format_indian_currency
from sqlalchemy import or_, and_
from difflib import SequenceMatcher
import re

search = Blueprint('search', __name__)

def similarity(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_text(text):
    """Normalize text for better matching"""
    if not text:
        return ""
    # Convert to lowercase and remove extra spaces
    text = re.sub(r'\s+', ' ', text.lower().strip())
    return text

def search_products(query, limit=20):
    """Search products with fuzzy matching"""
    if not query or len(query.strip()) < 2:
        return []
    
    normalized_query = normalize_text(query)
    query_words = normalized_query.split()
    
    # Get all products with their related data
    products = Product.query.all()
    results = []
    
    for product in products:
        score = 0
        matched_fields = []
        
        # Search in product name
        if product.name:
            product_name_normalized = normalize_text(product.name)
            for word in query_words:
                if word in product_name_normalized:
                    score += 10
                    matched_fields.append('name')
                else:
                    # Fuzzy matching for product name
                    name_similarity = similarity(word, product_name_normalized)
                    if name_similarity > 0.6:
                        score += int(name_similarity * 8)
                        matched_fields.append('name')
        
        # Search in keywords
        if product.keywords:
            keywords_normalized = normalize_text(product.keywords)
            for word in query_words:
                if word in keywords_normalized:
                    score += 8
                    matched_fields.append('keywords')
                else:
                    # Fuzzy matching for keywords
                    keyword_similarity = similarity(word, keywords_normalized)
                    if keyword_similarity > 0.6:
                        score += int(keyword_similarity * 6)
                        matched_fields.append('keywords')
        
        # Search in description
        if product.description:
            description_normalized = normalize_text(product.description)
            for word in query_words:
                if word in description_normalized:
                    score += 5
                    matched_fields.append('description')
                else:
                    # Fuzzy matching for description
                    desc_similarity = similarity(word, description_normalized)
                    if desc_similarity > 0.6:
                        score += int(desc_similarity * 4)
                        matched_fields.append('description')
        
        # Search in category name
        if product.category and product.category.name:
            category_name_normalized = normalize_text(product.category.name)
            for word in query_words:
                if word in category_name_normalized:
                    score += 7
                    matched_fields.append('category')
                else:
                    # Fuzzy matching for category
                    cat_similarity = similarity(word, category_name_normalized)
                    if cat_similarity > 0.6:
                        score += int(cat_similarity * 5)
                        matched_fields.append('category')
        
        # Search in subcategory name
        if product.subcategory and product.subcategory.name:
            subcategory_name_normalized = normalize_text(product.subcategory.name)
            for word in query_words:
                if word in subcategory_name_normalized:
                    score += 6
                    matched_fields.append('subcategory')
                else:
                    # Fuzzy matching for subcategory
                    subcat_similarity = similarity(word, subcategory_name_normalized)
                    if subcat_similarity > 0.6:
                        score += int(subcat_similarity * 4)
                        matched_fields.append('subcategory')
        
        # Search in seller username
        if product.seller and product.seller.username:
            seller_username_normalized = normalize_text(product.seller.username)
            for word in query_words:
                if word in seller_username_normalized:
                    score += 9
                    matched_fields.append('seller')
                else:
                    # Fuzzy matching for seller
                    seller_similarity = similarity(word, seller_username_normalized)
                    if seller_similarity > 0.6:
                        score += int(seller_similarity * 7)
                        matched_fields.append('seller')
        
        # Only include products with a minimum score
        if score > 0:
            # Get the first auction for this product (if any)
            auction = Auction.query.filter_by(product_id=product.id).first()
            
            results.append({
                'product': product,
                'auction': auction,
                'score': score,
                'matched_fields': list(set(matched_fields))  # Remove duplicates
            })
    
    # Sort by score (highest first) and limit results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]

def search_sellers(query, limit=10):
    """Search sellers with fuzzy matching"""
    if not query or len(query.strip()) < 2:
        return []
    
    normalized_query = normalize_text(query)
    query_words = normalized_query.split()
    
    sellers = User.query.filter_by(role='seller').all()
    results = []
    
    for seller in sellers:
        score = 0
        matched_fields = []
        
        # Search in seller username
        if seller.username:
            seller_username_normalized = normalize_text(seller.username)
            for word in query_words:
                if word in seller_username_normalized:
                    score += 10
                    matched_fields.append('username')
                else:
                    # Fuzzy matching for username
                    username_similarity = similarity(word, seller_username_normalized)
                    if username_similarity > 0.6:
                        score += int(username_similarity * 8)
                        matched_fields.append('username')
        
        # Search in seller email
        if seller.email:
            email_normalized = normalize_text(seller.email)
            for word in query_words:
                if word in email_normalized:
                    score += 5
                    matched_fields.append('email')
                else:
                    # Fuzzy matching for email
                    email_similarity = similarity(word, email_normalized)
                    if email_similarity > 0.6:
                        score += int(email_similarity * 4)
                        matched_fields.append('email')
        
        # Only include sellers with a minimum score
        if score > 0:
            results.append({
                'seller': seller,
                'score': score,
                'matched_fields': list(set(matched_fields))
            })
    
    # Sort by score and limit results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]

def search_categories(query, limit=10):
    """Search categories with fuzzy matching"""
    if not query or len(query.strip()) < 2:
        return []
    
    normalized_query = normalize_text(query)
    query_words = normalized_query.split()
    
    categories = Category.query.all()
    results = []
    
    for category in categories:
        score = 0
        matched_fields = []
        
        # Search in category name
        if category.name:
            category_name_normalized = normalize_text(category.name)
            for word in query_words:
                if word in category_name_normalized:
                    score += 10
                    matched_fields.append('name')
                else:
                    # Fuzzy matching for category name
                    name_similarity = similarity(word, category_name_normalized)
                    if name_similarity > 0.6:
                        score += int(name_similarity * 8)
                        matched_fields.append('name')
        
        # Only include categories with a minimum score
        if score > 0:
            results.append({
                'category': category,
                'score': score,
                'matched_fields': list(set(matched_fields))
            })
    
    # Sort by score and limit results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]

def search_subcategories(query, limit=10):
    """Search subcategories with fuzzy matching"""
    if not query or len(query.strip()) < 2:
        return []
    
    normalized_query = normalize_text(query)
    query_words = normalized_query.split()
    
    subcategories = Subcategory.query.all()
    results = []
    
    for subcategory in subcategories:
        score = 0
        matched_fields = []
        
        # Search in subcategory name
        if subcategory.name:
            subcategory_name_normalized = normalize_text(subcategory.name)
            for word in query_words:
                if word in subcategory_name_normalized:
                    score += 10
                    matched_fields.append('name')
                else:
                    # Fuzzy matching for subcategory name
                    name_similarity = similarity(word, subcategory_name_normalized)
                    if name_similarity > 0.6:
                        score += int(name_similarity * 8)
                        matched_fields.append('name')
        
        # Search in parent category name
        if subcategory.category and subcategory.category.name:
            category_name_normalized = normalize_text(subcategory.category.name)
            for word in query_words:
                if word in category_name_normalized:
                    score += 5
                    matched_fields.append('parent_category')
                else:
                    # Fuzzy matching for parent category
                    cat_similarity = similarity(word, category_name_normalized)
                    if cat_similarity > 0.6:
                        score += int(cat_similarity * 4)
                        matched_fields.append('parent_category')
        
        # Only include subcategories with a minimum score
        if score > 0:
            results.append({
                'subcategory': subcategory,
                'score': score,
                'matched_fields': list(set(matched_fields))
            })
    
    # Sort by score and limit results
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:limit]

def save_search_history(user_id, query, search_type):
    """Save search history for recommendations"""
    if user_id:
        search_history = SearchHistory(
            user_id=user_id,
            query=query,
            search_type=search_type
        )
        from .models import db
        db.session.add(search_history)
        db.session.commit()

@search.route('/search')
def search_page():
    """Search page route"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')  # all, products, categories, subcategories, sellers
    
    # Save search history if user is logged in
    user_id = session.get('user_id')
    if user_id and query:
        save_search_history(user_id, query, search_type)
    
    if not query:
        return render_template('search.html', 
                             query='', 
                             products=[], 
                             categories=[], 
                             subcategories=[],
                             sellers=[],
                             format_indian_currency=format_indian_currency)
    
    results = {
        'products': [],
        'categories': [],
        'subcategories': [],
        'sellers': []
    }
    
    if search_type in ['all', 'products']:
        results['products'] = search_products(query)
    
    if search_type in ['all', 'categories']:
        results['categories'] = search_categories(query)
    
    if search_type in ['all', 'subcategories']:
        results['subcategories'] = search_subcategories(query)
    
    if search_type in ['all', 'sellers']:
        results['sellers'] = search_sellers(query)
    
    return render_template('search.html',
                         query=query,
                         products=results['products'],
                         categories=results['categories'],
                         subcategories=results['subcategories'],
                         sellers=results['sellers'],
                         format_indian_currency=format_indian_currency)

@search.route('/api/search')
def api_search():
    """API endpoint for search suggestions"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    suggestions = []
    
    # Get product suggestions
    products = search_products(query, limit=5)
    for result in products:
        product = result['product']
        suggestions.append({
            'type': 'product',
            'id': product.id,
            'name': product.name,
            'category': product.category.name if product.category else '',
            'subcategory': product.subcategory.name if product.subcategory else '',
            'seller': product.seller.username if product.seller else '',
            'score': result['score'],
            'url': f'/auction/{product.auctions[0].id}' if product.auctions else None
        })
    
    # Get seller suggestions
    sellers = search_sellers(query, limit=3)
    for result in sellers:
        seller = result['seller']
        suggestions.append({
            'type': 'seller',
            'id': seller.id,
            'name': seller.username,
            'email': seller.email,
            'score': result['score'],
            'url': f'/search?q={seller.username}&type=sellers'
        })
    
    # Get category suggestions
    categories = search_categories(query, limit=3)
    for result in categories:
        category = result['category']
        suggestions.append({
            'type': 'category',
            'id': category.id,
            'name': category.name,
            'score': result['score'],
            'url': f'/search?q={category.name}&type=categories'
        })
    
    # Get subcategory suggestions
    subcategories = search_subcategories(query, limit=3)
    for result in subcategories:
        subcategory = result['subcategory']
        suggestions.append({
            'type': 'subcategory',
            'id': subcategory.id,
            'name': subcategory.name,
            'category': subcategory.category.name if subcategory.category else '',
            'score': result['score'],
            'url': f'/search?q={subcategory.name}&type=subcategories'
        })
    
    # Sort all suggestions by score
    suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({'suggestions': suggestions[:10]})
