from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api.routes import auth, products, seed
from app.seed import should_seed_database, seed_all_data
import os

app = FastAPI(title="Product Admin API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(seed.router)


@app.on_event("startup")
def startup_event():
    # Initialize database tables
    init_db()
    
    # Check if we should seed the database
    if should_seed_database():
        print("Auto-seeding database...")
        seed_all_data()
    else:
        print("Database already contains data, skipping seeding")


@app.get("/")
def root():
    return {"message": "Product Admin API is running"}
