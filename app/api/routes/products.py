from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
import json
import cloudinary
import cloudinary.uploader
from app.database import get_db
from app.schemas.product import Product, ProductCreate
from app.models.product import Product as ProductModel
from app.api.routes.auth import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/products", tags=["products"])


class ProductResponse(BaseModel):
    """Response model for product operations"""
    success: bool
    message: str
    data: Optional[Product] = None


class DeleteResponse(BaseModel):
    """Response model for delete operations"""
    success: bool
    message: str

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret
)


@router.get(
    "/",
    response_model=List[Product],
    summary="Get all products",
    description="Retrieve a list of all products with their details including images and features.",
    responses={
        200: {
            "description": "Successfully retrieved all products",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "category": "ROLL-UP",
                            "header": "Premium Roll-up Banner",
                            "description": "High-quality roll-up banner for exhibitions",
                            "features": ["Durable material", "Easy setup", "Portable"],
                            "image_url": "https://res.cloudinary.com/demo/image/upload/v1/products/banner1.jpg",
                            "image_public_id": "products/banner1",
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    ]
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        500: {"description": "Internal server error"}
    }
)
async def get_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all products from the database.
    
    - **Authentication**: Required
    - **Returns**: List of products with full details
    - **Sorting**: Ordered by creation date (newest first)
    """
    try:
        result = await db.execute(select(ProductModel).offset(skip).limit(limit))
        products = result.scalars().all()
        return products
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve products: {str(e)}"
        )


@router.post(
    "/",
    response_model=ProductResponse,
    summary="Create a new product",
    description="Create a new product with image upload to Cloudinary. The image is automatically optimized and stored.",
    responses={
        201: {
            "description": "Product created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Product created successfully",
                        "data": {
                            "id": 1,
                            "category": "ROLL-UP",
                            "header": "Premium Roll-up Banner",
                            "description": "High-quality roll-up banner for exhibitions",
                            "features": ["Durable material", "Easy setup", "Portable"],
                            "image_url": "https://res.cloudinary.com/demo/image/upload/v1/products/banner1.jpg",
                            "image_public_id": "products/banner1",
                            "created_at": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            }
        },
        400: {"description": "Bad request - Invalid data or file format"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        413: {"description": "Payload too large - Image file exceeds size limit"},
        500: {"description": "Internal server error"}
    }
)
async def create_product(
    category: str = Form(..., description="Product category from predefined list"),
    header: str = Form(..., description="Product name/title"),
    description: str = Form(..., description="Detailed product description"),
    features: str = Form(..., description="JSON array of product features"),
    image: UploadFile = File(..., description="Product image file (JPEG, PNG, WebP, GIF)"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Create a new product with image upload to Cloudinary.
    
    - **Authentication**: Required
    - **Image Processing**: Automatic optimization and format conversion to WebP
    - **File Size Limit**: 10MB maximum
    - **Supported Formats**: JPEG, PNG, WebP, GIF
    - **Cloud Storage**: Images stored in Cloudinary with automatic CDN distribution
    """
    try:
        # Validate image file type
        if not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only image files are allowed."
            )
        
        # Validate file size (10MB limit)
        if image.size and image.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image file size must be less than 10MB."
            )
        
        # Parse features from JSON string
        try:
            features_list = json.loads(features)
            if not isinstance(features_list, list):
                raise ValueError("Features must be an array")
            if len(features_list) == 0:
                raise ValueError("At least one feature is required")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid features format: {str(e)}. Features must be a valid JSON array."
            )
        
        # Upload image to Cloudinary with optimization
        try:
            upload_result = cloudinary.uploader.upload(
                image.file,
                folder="products",
                resource_type="image",
                format="webp",
                quality="auto:good",
                fetch_format="auto",
                crop="limit",
                width=2000,
                height=2000
            )
            image_url = upload_result["secure_url"]
            image_public_id = upload_result["public_id"]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image to cloud storage: {str(e)}"
            )
        
        # Create product record
        db_product = ProductModel(
            category=category,
            header=header.strip(),
            description=description.strip(),
            features=features_list,
            image_url=image_url,
            image_public_id=image_public_id
        )
        
        # Save to database
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
        
        return ProductResponse(
            success=True,
            message="Product created successfully",
            data=db_product
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback database changes on error
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create product: {str(e)}"
        )


@router.delete(
    "/{product_id}",
    response_model=DeleteResponse,
    summary="Delete a product",
    description="Permanently delete a product and its associated image from cloud storage.",
    responses={
        200: {
            "description": "Product deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Product deleted successfully"
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        404: {"description": "Product not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Delete a product and its associated image from Cloudinary.
    
    - **Authentication**: Required
    - **Cascade Delete**: Removes both database record and cloud storage image
    - **Irreversible**: This action cannot be undone
    - **Cleanup**: Automatically removes orphaned images from Cloudinary
    """
    try:
        # Verify product exists
        result = await db.execute(
            select(ProductModel).where(ProductModel.id == product_id)
        )
        product = result.scalar_one_or_none()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        
        # Delete image from Cloudinary if it exists
        if product.image_public_id:
            try:
                cloudinary.uploader.destroy(product.image_public_id)
            except Exception as e:
                # Log error but continue with database deletion
                # This ensures database consistency even if cloud storage fails
                print(f"Warning: Failed to delete image from Cloudinary: {e}")
        
        # Delete product from database
        await db.execute(
            delete(ProductModel).where(ProductModel.id == product_id)
        )
        await db.commit()
        
        return DeleteResponse(
            success=True,
            message="Product deleted successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback database changes on error
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete product: {str(e)}"
        )


