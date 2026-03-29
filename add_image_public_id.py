"""
Migration script to add image_public_id column to products table.
Run this script to update the database schema.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def add_image_public_id_column():
    """Add image_public_id column to products table if it doesn't exist."""
    engine = create_async_engine(settings.database_url)
    
    async with engine.begin() as conn:
        try:
            # Check if column already exists
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'products' AND column_name = 'image_public_id'
            """))
            
            if not result.fetchone():
                print("Adding image_public_id column to products table...")
                
                # Add the column
                await conn.execute(text("""
                    ALTER TABLE products 
                    ADD COLUMN image_public_id VARCHAR(255) NOT NULL DEFAULT ''
                """))
                
                print("Column added successfully!")
            else:
                print("image_public_id column already exists.")
                
        except Exception as e:
            print(f"Error during migration: {e}")
            raise
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_image_public_id_column())
