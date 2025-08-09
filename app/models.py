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
    
    # Relationships
    products = db.relationship('Product', backref='seller', lazy=True)
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    
    @property
    def status(self):
        """Determine auction status based on current time"""
        now = datetime.utcnow()
        
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
