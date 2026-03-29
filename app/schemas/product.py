from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.product import ProductCategory


class ProductBase(BaseModel):
    category: ProductCategory
    header: str
    description: str
    features: List[str]
    image_url: str
    image_public_id: str


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
