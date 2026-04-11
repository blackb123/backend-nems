"""
Temporary seeding endpoint for production use
Remove after initial deployment
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.seed import seed_all_data

router = APIRouter(prefix="/seed", tags=["seeding"])

@router.post("/force")
def force_seed_database(db: Session = Depends(get_db)):
    """Force seed the database - use only for initial setup"""
    try:
        # Seed the database and get detailed results
        results = seed_all_data()
        
        if not results["success"]:
            raise HTTPException(status_code=500, detail=f"Seeding failed: {results.get('error', 'Unknown error')}")
        
        return {
            "message": "Database seeded successfully!",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Seeding failed: {str(e)}")

@router.get("/status")
def check_seeding_status(db: Session = Depends(get_db)):
    """Check if database has been seeded"""
    from app.models.user import User
    from app.models.product import Product
    
    user_count = db.query(User).count()
    product_count = db.query(Product).count()
    
    return {
        "users": user_count,
        "products": product_count,
        "seeded": user_count > 0 and product_count > 0
    }
