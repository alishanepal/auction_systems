from app import create_app
from app.models import db, Category, Subcategory

app = create_app()

def init_categories():
    # Sample categories and subcategories
    categories = [
        {
            'name': 'Electronics',
            'subcategories': [
                {'name': 'Smartphones'},
                {'name': 'Laptops'},
                {'name': 'Headsets'},
                {'name': 'Tablets'},
                {'name': 'Audio'}
            ]
        },
        {
            'name': 'Fashion',
            'subcategories': [
                {'name': 'Men\'s Clothing'},
                {'name': 'Women\'s Clothing'},
                {'name': 'Shoes'},
                {'name': 'Accessories'}
            ]
        },
        {
            'name': 'Home & Garden',
            'subcategories': [
                {'name': 'Furniture'},
                {'name': 'Kitchen'},
                {'name': 'Decor'},
                {'name': 'Garden'}
            ]
        },
        {
            'name': 'Art & Collectibles',
            'subcategories': [
                {'name': 'Paintings'},
                {'name': 'Antiques'},
                {'name': 'Coins'},
                {'name': 'Sculptures'}
            ]
        }
    ]
    
    # Add categories and subcategories to database
    for category_data in categories:
        # Check if category already exists
        existing_category = Category.query.filter_by(name=category_data['name']).first()
        if not existing_category:
            # Create new category
            category = Category(name=category_data['name'])
            db.session.add(category)
            db.session.flush()  # Flush to get the category ID
            
            # Add subcategories
            for subcategory_data in category_data['subcategories']:
                subcategory = Subcategory(
                    name=subcategory_data['name'],
                    category_id=category.id
                )
                db.session.add(subcategory)
    
    # Commit changes
    db.session.commit()
    print('Categories and subcategories initialized successfully!')

if __name__ == '__main__':
    with app.app_context():
        init_categories()