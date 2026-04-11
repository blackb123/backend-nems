"""
Database seeding module for NEMS product management system
Automatically seeds admin users and sample products on startup
"""
import warnings
import hashlib
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models.user import User
from app.models.product import Product

warnings.filterwarnings("ignore", category=UserWarning)

# Admin users configuration
ADMIN_USERS = [
    {
        "username": "admin",
        "password": "admin123"
    },
    {
        "username": "super",
        "password": "super123"
    },
    {
        "username": "manager",
        "password": "manager456"
    },
    {
        "username": "director",
        "password": "director789"
    },
    {
        "username": "root",
        "password": "root2024"
    }
]


def simple_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def seed_admin_users(db: Session) -> None:
    print("Seeding admin users...")
    
    for admin_data in ADMIN_USERS:
        username = admin_data["username"]
        password = admin_data["password"]
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"  - Admin user '{username}' already exists")
            continue
        
        try:
            # Create new user
            password_hash = simple_hash(password)
            user = User(username=username, password_hash=password_hash)
            db.add(user)
            print(f"  + Created admin user: {username}")
        except Exception as e:
            print(f"  - Error creating admin user {username}: {e}")
            continue
    
    db.commit()
    print("Admin users seeding completed!")


def seed_database_from_file(db: Session, file_path: str = "seed_products.json") -> bool:
    """Seed products from JSON file if it exists. Returns True if successful."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        print(f"Seeding products from {file_path}...")
        products_created = 0
        
        for product_data in products_data:
            # Check if product already exists
            existing_product = db.query(Product).filter(Product.header == product_data["header"]).first()
            if existing_product:
                print(f"  - Product '{product_data['header']}' already exists")
                continue
            
            try:
                # Create product with your JSON structure
                product = Product(
                    header=product_data["header"],
                    description=product_data["description"],
                    category=product_data["category"],
                    features=product_data.get("features", []),
                    images=product_data.get("images", []),  # JSON array of image objects
                    is_active=product_data.get("is_active", True),
                    primary_image_index=0  # First image will be primary
                )
                db.add(product)
                products_created += 1
                print(f"  + Created product: {product_data['header']}")
                
            except Exception as e:
                print(f"  - Error creating product {product_data['header']}: {e}")
                continue
        
        db.commit()
        print(f"Products seeding from {file_path} completed! Created {products_created} products.")
        return products_created > 0
        
    except FileNotFoundError:
        print(f"  - Seed file {file_path} not found, skipping")
        return False
    except json.JSONDecodeError as e:
        print(f"  - Error parsing {file_path}: {e}")
        return False
    except Exception as e:
        print(f"  - Error seeding from {file_path}: {e}")
        return False

def seed_all_data() -> dict:
    """Main seeding function - seeds all data and returns results"""
    print("=== NEMS Database Seeding Started ===")
    
    # Initialize database tables
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get counts before seeding
        users_before = db.query(User).count()
        products_before = db.query(Product).count()
        
        # Seed admin users
        seed_admin_users(db)
        
        # Seed products from JSON file
        products_created = seed_database_from_file(db, "seed_products.json")
        
        # Get counts after seeding
        users_after = db.query(User).count()
        products_after = db.query(Product).count()
        
        # Get some sample products for visualization
        sample_products = db.query(Product).limit(5).all()
        product_list = []
        for product in sample_products:
            product_list.append({
                "header": product.header,
                "category": product.category,
                "description": product.description[:100] + "..." if len(product.description) > 100 else product.description,
                "features_count": len(product.features) if product.features else 0,
                "images_count": len(product.images) if product.images else 0,
                "is_active": product.is_active
            })
        
        print("\n=== Database Seeding Completed Successfully! ===")
        
        # Display admin credentials
        print("\n=== ADMIN USER CREDENTIALS ===")
        for i, admin_data in enumerate(ADMIN_USERS, 1):
            print(f"{i}. Username: {admin_data['username']}")
            print(f"   Password: {admin_data['password']}")
            print()
        
        # Display product summary
        print(f"=== PRODUCTS SUMMARY ===")
        print(f"Total Products: {products_after}")
        print(f"Products Created: {products_after - products_before}")
        
        return {
            "success": True,
            "admin_users": {
                "before": users_before,
                "after": users_after,
                "created": users_after - users_before,
                "credentials": [
                    {"username": admin["username"], "password": admin["password"]} 
                    for admin in ADMIN_USERS
                ]
            },
            "products": {
                "before": products_before,
                "after": products_after,
                "created": products_after - products_before,
                "source": "seed_products.json",
                "sample_products": product_list
            }
        }
        
    except Exception as e:
        print(f"Error during database seeding: {e}")
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()

def is_production_environment() -> bool:
    import os
    return os.getenv("RAILWAY_ENVIRONMENT") == "production" or \
           os.getenv("RENDER") == "true" or \
           os.getenv("ENVIRONMENT") == "production"

def should_seed_database() -> bool:
    """Determine if database should be seeded"""
    import os
    
    # Always seed if explicitly requested
    if os.getenv("SEED_DATABASE", "false").lower() == "true":
        return True
    
    # Auto-seed in production if database is empty
    if is_production_environment():
        try:
            db = SessionLocal()
            user_count = db.query(User).count()
            product_count = db.query(Product).count()
            db.close()
            
            # Seed if no users or products exist
            return user_count == 0 or product_count == 0
        except:
            # If we can't connect, assume we need to seed
            return True
    
    return False

if __name__ == "__main__":
    # Run seeding if called directly
    seed_all_data()
elif should_seed_database():
    # Auto-seed on startup in production
    seed_all_data()
