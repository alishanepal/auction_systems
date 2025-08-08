from app import create_app, db
from app.models import Category, Subcategory

app = create_app()
with app.app_context():
    categories = Category.query.all()
    print(f"Found {len(categories)} categories:")
    for category in categories:
        print(f"Category ID: {category.id}, Name: {category.name}")
        subcategories = Subcategory.query.filter_by(category_id=category.id).all()
        print(f"  Subcategories ({len(subcategories)}):")  
        for subcategory in subcategories:
            print(f"    - ID: {subcategory.id}, Name: {subcategory.name}")