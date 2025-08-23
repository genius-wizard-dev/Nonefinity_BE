from app.models.base import BaseDocument
from app.models.user import User
from app.models.product import Product, Category, ProductStatus

# Export all models for easy import
__all__ = [
    "BaseDocument",
    "User", 
    "Product",
    "Category",
    "ProductStatus"
]

# List of all document models for Beanie initialization
DOCUMENT_MODELS = [
    User,
    Product,
    Category
]
