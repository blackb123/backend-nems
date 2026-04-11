from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import Enum

Base = declarative_base()


class ProductCategory(str, Enum):
    ROLL_UP = "ROLL-UP"
    X_BANNER = "X-BANNER"
    FLYING_BANNER = "FLYING BANNER"
    BACKDROPS = "BACKDROPS"
    STOP_TROTTOIRS = "STOP TROTTOIRS"
    SIGNALETIQUE = "SIGNALETIQUE"
    CADRES_MURAUX = "CADRES MURAUX"
    STOP_RAYON = "STOP RAYON"
    PLV = "PLV"
    CHEVALETS = "CHEVALETS"
    PORTES_BROCHURES = "PORTES BROCHURES"
    GONFLABLE = "GONFLABLE"
    CHAPITAUX = "CHAPITAUX"
    ENSEIGNES = "ENSEIGNES"
    IMPRESSION_NUMERIQUE = "IMPRESSION NUMERIQUE"
    SERIGRAPHIE = "SERIGRAPHIE"
    BRODERIE = "BRODERIE"
    TEXTILE = "TEXTILE"
    GADGETS = "GADGETS"
    OTHERS = "OTHERS"


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint('category', 'header', name='uq_product_category_header'),
    )

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    header = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    features = Column(JSON, nullable=False)
    
    # Multiple image support (up to 5 images)
    images = Column(JSON, nullable=False)  # List of image objects with url, public_id, and order
    primary_image_index = Column(Integer, default=0)  # Index of primary image in images array
    
    is_active = Column(Boolean, default=True)  # Soft delete support
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
