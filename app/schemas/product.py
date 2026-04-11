from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.product import ProductCategory


class ImageInfo(BaseModel):
    """Schema for individual image information"""
    url: str
    public_id: str
    order: int = 0
    
    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    category: ProductCategory
    header: str
    description: str
    features: List[str]
    images: List[ImageInfo]
    primary_image_index: int = 0
    
    @validator('images')
    def validate_images(cls, v):
        if len(v) == 0:
            raise ValueError('At least one image is required')
        if len(v) > 4:
            raise ValueError('Maximum 4 images allowed')
        return v
    
    @validator('primary_image_index')
    def validate_primary_image_index(cls, v, values):
        if 'images' in values and (v < 0 or v >= len(values['images'])):
            raise ValueError('Primary image index must be valid')
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    category: Optional[ProductCategory] = None
    header: Optional[str] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    images: Optional[List[ImageInfo]] = None
    primary_image_index: Optional[int] = None
    is_active: Optional[bool] = None
    
    @validator('images')
    def validate_images(cls, v):
        if v is not None:
            if len(v) == 0:
                raise ValueError('At least one image is required')
            if len(v) > 4:
                raise ValueError('Maximum 4 images allowed')
        return v


class Product(ProductBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    """Response model for product operations"""
    success: bool
    message: str
    data: Optional[Product] = None


class DeleteResponse(BaseModel):
    """Response model for delete operations"""
    success: bool
    message: str


class ProductList(BaseModel):
    """Response model for product list with pagination"""
    products: List[Product]
    total: int
    skip: int
    limit: int
