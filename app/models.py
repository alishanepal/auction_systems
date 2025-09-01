from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'bidder' or 'seller'
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'accepted', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    products = db.relationship('Product', backref='seller', lazy=True)
    bids = db.relationship('Bid', backref='bidder', lazy=True)
    won_auctions = db.relationship('AuctionResult', backref='winner', lazy=True)
    search_history = db.relationship('SearchHistory', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    # Relationships
    subcategories = db.relationship('Subcategory', backref='category', lazy=True)
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'


class Subcategory(db.Model):
    __tablename__ = 'subcategories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # Relationships
    products = db.relationship('Product', backref='subcategory', lazy=True)
    
    def __repr__(self):
        return f'<Subcategory {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    starting_bid = db.Column(db.Float, nullable=False)
    reserve_price = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    keywords = db.Column(db.String(255), nullable=True)
    minimum_interval = db.Column(db.Float, nullable=False, default=1.0)  # Minimum bid increment
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)  # Store the path to the uploaded image
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    auctions = db.relationship('Auction', backref='product', lazy=True)
    
    def __repr__(self):
        return f'<Product {self.name}>'


class Auction(db.Model):
    __tablename__ = 'auctions'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    type = db.Column(db.String(20), nullable=False, default='auction')  # auction, buy_now, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bids = db.relationship('Bid', backref='auction', lazy=True)
    result = db.relationship('AuctionResult', backref='auction', uselist=False, lazy=True)
    
    @property
    def status(self):
        """Determine auction status based on current time"""
        now = datetime.now()  # Use local time instead of UTC
        
        if now < self.start_date:
            return 'upcoming'
        elif now >= self.start_date and now < self.end_date:
            return 'live'
        else:
            return 'ended'
            
    def update_status(self):
        """Legacy method for compatibility - returns current status"""
        return self.status
    
    def __repr__(self):
        return f'<Auction {self.id} for Product {self.product_id}>'


class Bid(db.Model):
    __tablename__ = 'bids'
    
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=False)
    bidder_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bid_amount = db.Column(db.Float, nullable=False)
    bid_time = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Bid {self.id} by User {self.bidder_id} on Auction {self.auction_id}>'


class AuctionResult(db.Model):
    __tablename__ = 'auction_results'
    
    id = db.Column(db.Integer, primary_key=True)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=False, unique=True)
    winner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    winning_bid = db.Column(db.Float, nullable=False)
    ended_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<AuctionResult {self.id} for Auction {self.auction_id}>'


class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query = db.Column(db.String(255), nullable=False)
    search_type = db.Column(db.String(20), nullable=False, default='all')  # all, products, categories, subcategories, sellers
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<SearchHistory {self.id} by User {self.user_id}>'


class BidHistory(db.Model):
    __tablename__ = 'bid_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bid_count = db.Column(db.Integer, nullable=True)
    last_bid_time = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    product = db.relationship('Product', foreign_keys=[product_id])
    category = db.relationship('Category', foreign_keys=[category_id])
    subcategory = db.relationship('Subcategory', foreign_keys=[subcategory_id])
    seller = db.relationship('User', foreign_keys=[seller_id])
    user = db.relationship('User', foreign_keys=[user_id], backref='bid_history_entries')
    
    def __repr__(self):
        return f'<BidHistory {self.id} user={self.user_id} product={self.product_id} count={self.bid_count}>'


class Wishlist(db.Model):
    __tablename__ = 'wishlist'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='wishlist_entries')
    product = db.relationship('Product', foreign_keys=[product_id])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', name='uq_wishlist_user_product'),
    )

    def __repr__(self):
        return f'<Wishlist id={self.id} user={self.user_id} product={self.product_id}>'


class BidderMinimumAmount(db.Model):
    __tablename__ = 'bidder_minimum_amounts'
    
    id = db.Column(db.Integer, primary_key=True)
    bidder_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    auction_id = db.Column(db.Integer, db.ForeignKey('auctions.id'), nullable=False)
    minimum_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    bidder = db.relationship('User', foreign_keys=[bidder_id], backref='minimum_amounts')
    product = db.relationship('Product', foreign_keys=[product_id])
    auction = db.relationship('Auction', foreign_keys=[auction_id])
    
    # Get seller through product relationship
    @property
    def seller(self):
        return self.product.seller if self.product else None
    
    # Get seller_id through product relationship
    @property
    def seller_id(self):
        return self.product.seller_id if self.product else None
    
    __table_args__ = (
        db.UniqueConstraint('bidder_id', 'auction_id', name='uq_bidder_minimum_amount_bidder_auction'),
    )
    
    def __repr__(self):
        return f'<BidderMinimumAmount id={self.id} bidder={self.bidder_id} auction={self.auction_id} amount={self.minimum_amount}>'
    
    @classmethod
    def set_minimum_amount(cls, bidder_id, auction_id, product_id, minimum_amount):
        """Set or update minimum amount for a bidder on a specific auction"""
        existing = cls.query.filter_by(bidder_id=bidder_id, auction_id=auction_id).first()
        if existing:
            existing.minimum_amount = minimum_amount
            existing.updated_at = datetime.now()
            db.session.commit()
            return existing
        else:
            new_minimum = cls(
                bidder_id=bidder_id,
                auction_id=auction_id,
                product_id=product_id,
                minimum_amount=minimum_amount
            )
            db.session.add(new_minimum)
            db.session.commit()
            return new_minimum
    
    @classmethod
    def get_minimum_amount(cls, bidder_id, auction_id):
        """Get minimum amount for a bidder on a specific auction"""
        record = cls.query.filter_by(bidder_id=bidder_id, auction_id=auction_id).first()
        return record.minimum_amount if record else None
    
    @classmethod
    def get_bidder_minimums(cls, bidder_id):
        """Get all minimum amounts set by a specific bidder"""
        return cls.query.filter_by(bidder_id=bidder_id).all()
    
    @classmethod
    def get_auction_minimums(cls, auction_id):
        """Get all minimum amounts set for a specific auction"""
        return cls.query.filter_by(auction_id=auction_id).all()
