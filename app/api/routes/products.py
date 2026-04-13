from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from typing import List, Optional, Union
import json
import cloudinary
import cloudinary.uploader
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.database import get_db
from app.schemas.product import (
    Product, ProductCreate, ProductUpdate, ProductResponse,
    DeleteResponse, ProductList, ImageInfo
)
from app.models.product import Product as ProductModel, ProductCategory
from app.api.routes.auth import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/products", tags=["products"])

# ------------------------------------------------------------------
# Cloudinary Configuration
# ------------------------------------------------------------------
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret
)

# Default fallback image
NEM_LOGO_IMAGE = {
    "url": "/logo_nems.webp",
    "public_id": "nems_logo",
    "order": 0
}

# ------------------------------------------------------------------
# Validation & Utility Functions
# ------------------------------------------------------------------
def validate_image_file(image: UploadFile) -> None:
    """Check file type and size before upload."""
    if not image.content_type.startswith("image/"):
        logger.warning(f"Invalid file type: {image.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_FILE_TYPE",
                "message": "Only image files are allowed.",
                "field": "image",
                "accepted_types": ["image/jpeg", "image/png", "image/webp"]
            }
        )
    if image.size and image.size > 10 * 1024 * 1024:  # 10 MB
        logger.warning(f"File too large: {image.size} bytes")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "FILE_TOO_LARGE",
                "message": "Image must be smaller than 10MB.",
                "field": "image",
                "max_size": "10MB",
                "received_size": f"{image.size / (1024*1024):.1f}MB"
            }
        )

async def upload_image_to_cloudinary(image: UploadFile, folder: str = "products") -> dict:
    """Upload an image to Cloudinary and return secure URL and public_id."""
    try:
        logger.info(f"Uploading image: {image.filename} to folder: {folder}")
        result = cloudinary.uploader.upload(
            image.file,
            folder=folder,
            resource_type="image",
            format="webp",
            quality="auto:good",
            fetch_format="auto",
            crop="limit",
            width=2000,
            height=2000
        )
        logger.info(f"Successfully uploaded: {result['public_id']}")
        return {"url": result["secure_url"], "public_id": result["public_id"]}
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "UPLOAD_FAILED",
                "message": f"Cloud upload failed: {str(e)}",
                "field": "image",
                "service": "cloudinary"
            }
        )

def delete_image_from_cloudinary(public_id: str) -> None:
    """Delete an image from Cloudinary (never delete the NEM logo)."""
    if public_id == "nems_logo":
        return
    try:
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        # Log the error but do not break the flow
        print(f"Warning: Could not delete image {public_id}: {e}")

def parse_features_json(features_str: str) -> List[str]:
    """Convert a JSON string into a list of feature strings."""
    try:
        features = json.loads(features_str)
        if not isinstance(features, list) or not features:
            logger.warning(f"Invalid features format: {features_str}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_FEATURES_FORMAT",
                    "message": "Features must be a non-empty array.",
                    "field": "features",
                    "expected_format": "JSON array of strings",
                    "received": features_str
                }
            )
        return features
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Features parsing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_FEATURES_FORMAT",
                "message": f"Invalid features format: {e}",
                "field": "features",
                "expected_format": "JSON array of strings"
            }
        )

def validate_category(category: str) -> None:
    """Ensure the provided category exists in the ProductCategory enum."""
    try:
        ProductCategory(category)
        logger.info(f"Valid category: {category}")
    except ValueError:
        logger.warning(f"Invalid category: {category}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_CATEGORY",
                "message": f"Invalid category: {category}",
                "field": "category",
                "valid_categories": [c.value for c in ProductCategory]
            }
        )

# ------------------------------------------------------------------
# Business Logic Helpers (Database Operations)
# ------------------------------------------------------------------
def get_product_or_404(db: Session, product_id: int) -> ProductModel:
    """Fetch a product by ID or raise 404."""
    product = db.get(ProductModel, product_id)
    if not product:
        logger.warning(f"Product not found: {product_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "PRODUCT_NOT_FOUND",
                "message": f"Product {product_id} not found",
                "field": "id",
                "product_id": product_id
            }
        )
    return product

def build_product_query(db: Session, category: Optional[str], is_active: bool):
    """Construct base query for listing products with optional category filter."""
    query = select(ProductModel).where(ProductModel.is_active == is_active)
    if category:
        validate_category(category)
        query = query.where(ProductModel.category == category)
    return query

# ------------------------------------------------------------------
# Image Handling Helpers
# ------------------------------------------------------------------
async def upload_multiple_images(images: List[UploadFile]) -> List[dict]:
    """Upload a list of images and return list of image info dicts."""
    uploaded = []
    for idx, img in enumerate(images):
        validate_image_file(img)
        result = await upload_image_to_cloudinary(img)
        uploaded.append({
            "url": result["url"],
            "public_id": result["public_id"],
            "order": idx
        })
    return uploaded

def remove_images_by_public_id(current_images: List[dict], ids_to_remove: List[str]) -> List[dict]:
    """Filter out images whose public_id is in ids_to_remove, deleting them from Cloudinary."""
    remaining = []
    for img in current_images:
        if img.get("public_id") in ids_to_remove:
            delete_image_from_cloudinary(img["public_id"])
        else:
            remaining.append(img)
    return remaining

def ensure_valid_primary_index(primary_index: Optional[int], total_images: int) -> int:
    """Return a safe primary image index."""
    if primary_index is None:
        return 0
    if primary_index < 0 or primary_index >= total_images:
        return 0
    return primary_index

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@router.get("/", response_model=ProductList)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(True),
    db: Session = Depends(get_db),
):
    """Get a paginated list of products, optionally filtered by category."""
    try:
        query = build_product_query(db, category, is_active)

        # Count total matching records
        total = db.execute(select(func.count()).select_from(query.subquery())).scalar()

        # Apply pagination
        query = query.order_by(ProductModel.created_at.desc()).offset(skip).limit(limit)
        products = db.execute(query).scalars().all()

        logger.info(f"Retrieved {len(products)} products (total: {total})")
        return ProductList(
            products=products,
            total=total,
            skip=skip,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Could not retrieve products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Could not retrieve products",
                "details": str(e),
                "operation": "list_products"
            }
        )

@router.get("/{product_id}", response_model=Product)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Get a single active product by its ID."""
    product = get_product_or_404(db, product_id)
    if not product.is_active:
        logger.warning(f"Inactive product accessed: {product_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "PRODUCT_NOT_FOUND",
                "message": "Product not found",
                "field": "id",
                "product_id": product_id
            }
        )
    return product

@router.get("/categories/list")
def list_categories(current_user: str = Depends(get_current_user)):
    """Return all available product categories."""
    return {"categories": [c.value for c in ProductCategory]}

@router.post("/", response_model=ProductResponse)
async def create_new_product(
    category: str = Form(...),
    header: str = Form(...),
    description: str = Form(...),
    features: str = Form(...),
    primary_image_index: int = Form(0),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Create a product with multiple images."""
    # --- Validation ---
    logger.info(f"Creating product: {header}")
    validate_category(category)
    if not images:
        logger.warning("No images provided for product creation")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "NO_IMAGES",
                "message": "At least one image is required.",
                "field": "images",
                "required": true
            }
        )
    if len(images) > 4:
        logger.warning(f"Too many images: {len(images)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "TOO_MANY_IMAGES",
                "message": "Maximum 4 images allowed.",
                "field": "images",
                "max_allowed": 4,
                "received": len(images)
            }
        )
    if primary_image_index < 0 or primary_image_index >= len(images):
        logger.warning(f"Invalid primary image index: {primary_image_index}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_PRIMARY_INDEX",
                "message": "Invalid primary image index.",
                "field": "primary_image_index",
                "valid_range": f"0-{len(images)-1}",
                "received": primary_image_index
            }
        )

    features_list = parse_features_json(features)

    # --- Upload images ---
    logger.info(f"Uploading {len(images)} images for product: {header}")
    uploaded_images = await upload_multiple_images(images)

    # --- Create DB record ---
    product = ProductModel(
        category=category,
        header=header.strip(),
        description=description.strip(),
        features=features_list,
        images=uploaded_images,
        primary_image_index=primary_image_index,
        is_active=True
    )

    try:
        logger.info(f"Creating product in database: {header}")
        db.add(product)
        db.commit()
        db.refresh(product)
        logger.info(f"Product created successfully: {product.id}")
        return ProductResponse(
            success=True,
            message="Product created successfully",
            data=product
        )
    except Exception as e:
        logger.error(f"Database error creating product: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Failed to create product",
                "details": str(e),
                "operation": "create_product"
            }
        )

@router.put("/{product_id}", response_model=ProductResponse)
async def update_existing_product(
    product_id: int,
    category: Optional[str] = Form(None),
    header: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    features: Optional[str] = Form(None),
    primary_image_index: Optional[int] = Form(None),
    new_images: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    image_ids_to_remove: Optional[str] = Form(None),  # JSON array of public_ids
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Update a product. Only provided fields are changed.
    Images can be added and/or removed by public_id.
    """
    product = get_product_or_404(db, product_id)

    # --- Update text fields if provided ---
    if category is not None:
        validate_category(category)
        product.category = category
    if header is not None:
        product.header = header.strip()
    if description is not None:
        product.description = description.strip()
    if features is not None:
        product.features = parse_features_json(features)

    # --- Handle image updates ---
    logger.info(f"Updating product {product_id}: {header or '(no change)'}")
    current_images = product.images.copy() if product.images else []

    # Remove specified images
    if image_ids_to_remove:
        try:
            ids_list = json.loads(image_ids_to_remove)
            if not isinstance(ids_list, list):
                raise ValueError("Must be a JSON array.")
            logger.info(f"Removing {len(ids_list)} images")
            current_images = remove_images_by_public_id(current_images, ids_list)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid image_ids_to_remove format: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_IMAGE_IDS",
                    "message": f"Invalid image IDs format: {e}",
                    "field": "image_ids_to_remove",
                    "expected_format": "JSON array of strings"
                }
            )

    # Add new images
    if new_images:
        # Normalize to list
        images_to_add = new_images if isinstance(new_images, list) else [new_images]
        logger.info(f"Adding {len(images_to_add)} new images")

        if len(current_images) + len(images_to_add) > 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "TOO_MANY_IMAGES",
                    "message": "Total images cannot exceed 4.",
                    "field": "images",
                    "current_count": len(current_images),
                    "new_count": len(images_to_add),
                    "max_allowed": 4
                }
            )

        uploaded = await upload_multiple_images(images_to_add)
        # Adjust order numbers for consistency
        start_order = len(current_images)
        for idx, img_info in enumerate(uploaded):
            img_info["order"] = start_order + idx
        current_images.extend(uploaded)

    # Fallback to default logo if no images remain
    if not current_images:
        current_images = [NEM_LOGO_IMAGE.copy()]

    # Update primary image index safely
    product.primary_image_index = ensure_valid_primary_index(
        primary_image_index, len(current_images)
    )
    product.images = current_images

    try:
        logger.info(f"Committing product update: {product_id}")
        db.commit()
        db.refresh(product)
        logger.info(f"Product updated successfully: {product.id}")
        return ProductResponse(
            success=True,
            message="Product updated successfully",
            data=product
        )
    except Exception as e:
        logger.error(f"Database error updating product: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Failed to update product",
                "details": str(e),
                "operation": "update_product",
                "product_id": product_id
            }
        )

@router.delete("/{product_id}", response_model=DeleteResponse)
def soft_delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Soft-delete a product by setting is_active=False."""
    logger.info(f"Deleting product {product_id} by user {current_user}")
    product = get_product_or_404(db, product_id)
    product.is_active = False
    try:
        logger.info(f"Soft-deleting product: {product_id}")
        db.commit()
        return DeleteResponse(success=True, message="Product deactivated")
    except Exception as e:
        logger.error(f"Delete operation failed: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DELETE_FAILED",
                "message": "Failed to delete product",
                "details": str(e),
                "operation": "delete_product",
                "product_id": product_id
            }
        )