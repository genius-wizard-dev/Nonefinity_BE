from typing import Optional, List, Dict, Any
from enum import Enum
from beanie import Indexed
from pydantic import Field, validator
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT

from app.models.base import BaseDocument


class ProductStatus(str, Enum):
    """Product status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


class Category(BaseDocument):
    """Product category model"""
    
    name: Indexed(str, unique=True) = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(default=None, max_length=500, description="Category description")
    slug: Indexed(str, unique=True) = Field(..., description="URL-friendly category identifier")
    parent_id: Optional[str] = Field(default=None, description="Parent category ID for hierarchy")
    is_active: bool = Field(default=True, description="Whether category is active")
    sort_order: int = Field(default=0, description="Display order")
    
    class Settings:
        collection = "categories"
        indexes = [
            IndexModel([("parent_id", ASCENDING)]),
            IndexModel([("is_active", ASCENDING), ("sort_order", ASCENDING)]),
            IndexModel([("name", TEXT)])
        ]


class Product(BaseDocument):
    """Product model with comprehensive indexing for testing"""
    
    # Basic product information
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: Optional[str] = Field(default=None, max_length=2000, description="Product description")
    short_description: Optional[str] = Field(default=None, max_length=500, description="Short product description")
    
    # Identifiers and SKU
    sku: Indexed(str, unique=True) = Field(..., description="Stock Keeping Unit")
    barcode: Optional[Indexed(str)] = Field(default=None, description="Product barcode")
    
    # Pricing
    price: Indexed(float) = Field(..., gt=0, description="Product price")
    cost_price: Optional[float] = Field(default=None, ge=0, description="Cost price")
    compare_price: Optional[float] = Field(default=None, ge=0, description="Compare at price")
    
    # Inventory
    stock_quantity: int = Field(default=0, ge=0, description="Available stock quantity")
    track_inventory: bool = Field(default=True, description="Whether to track inventory")
    allow_backorder: bool = Field(default=False, description="Allow orders when out of stock")
    
    # Categorization
    category_id: Indexed(str) = Field(..., description="Category ID")
    tags: List[str] = Field(default_factory=list, description="Product tags")
    brand: Optional[str] = Field(default=None, max_length=100, description="Product brand")
    
    # Status and visibility
    status: ProductStatus = Field(default=ProductStatus.DRAFT, description="Product status")
    is_featured: bool = Field(default=False, description="Whether product is featured")
    is_digital: bool = Field(default=False, description="Whether product is digital")
    
    # SEO and metadata
    slug: Indexed(str, unique=True) = Field(..., description="URL-friendly product identifier")
    meta_title: Optional[str] = Field(default=None, max_length=60, description="SEO title")
    meta_description: Optional[str] = Field(default=None, max_length=160, description="SEO description")
    
    # Media
    images: List[str] = Field(default_factory=list, description="Product image URLs")
    thumbnail: Optional[str] = Field(default=None, description="Thumbnail image URL")
    
    # Attributes and variants
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Product attributes")
    weight: Optional[float] = Field(default=None, ge=0, description="Product weight in kg")
    dimensions: Optional[Dict[str, float]] = Field(default=None, description="Product dimensions (length, width, height)")
    
    # Analytics
    view_count: int = Field(default=0, ge=0, description="Number of views")
    sales_count: int = Field(default=0, ge=0, description="Number of sales")
    rating_average: Optional[float] = Field(default=None, ge=0, le=5, description="Average rating")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings")
    
    @validator('price', 'cost_price', 'compare_price')
    def validate_prices(cls, v):
        if v is not None and v < 0:
            raise ValueError('Price cannot be negative')
        return v
    
    @validator('dimensions')
    def validate_dimensions(cls, v):
        if v is not None:
            required_keys = {'length', 'width', 'height'}
            if not required_keys.issubset(v.keys()):
                raise ValueError('Dimensions must include length, width, and height')
            for key, value in v.items():
                if value < 0:
                    raise ValueError(f'Dimension {key} cannot be negative')
        return v
    
    class Settings:
        collection = "products"
        indexes = [
            # Basic search indexes
            IndexModel([("name", TEXT), ("description", TEXT), ("tags", TEXT)]),
            
            # Price range queries
            IndexModel([("price", ASCENDING)]),
            IndexModel([("price", DESCENDING)]),
            
            # Category and status filtering
            IndexModel([("category_id", ASCENDING), ("status", ASCENDING)]),
            
            # Featured products
            IndexModel([("is_featured", ASCENDING), ("status", ASCENDING)]),
            
            # Inventory tracking
            IndexModel([("stock_quantity", ASCENDING), ("track_inventory", ASCENDING)]),
            
            # Brand filtering
            IndexModel([("brand", ASCENDING)]),
            
            # Popular products (by sales and views)
            IndexModel([("sales_count", DESCENDING)]),
            IndexModel([("view_count", DESCENDING)]),
            
            # Rating-based sorting
            IndexModel([("rating_average", DESCENDING), ("rating_count", DESCENDING)]),
            
            # Compound indexes for common queries
            IndexModel([("status", ASCENDING), ("is_featured", ASCENDING), ("price", ASCENDING)]),
            IndexModel([("category_id", ASCENDING), ("price", ASCENDING)]),
            IndexModel([("brand", ASCENDING), ("price", ASCENDING)]),
            
            # Date-based queries
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("updated_at", DESCENDING)])
        ]
