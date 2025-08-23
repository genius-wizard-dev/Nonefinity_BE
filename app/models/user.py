from datetime import datetime
from typing import Optional, List
from beanie import Indexed
from pydantic import EmailStr, Field
from pymongo import IndexModel, ASCENDING, TEXT

from app.models.base import BaseDocument


class User(BaseDocument):
    """User model with various indexed fields for testing"""
    
    # Basic user information
    email: Indexed(EmailStr, unique=True) = Field(..., description="User email address")
    username: Indexed(str, unique=True) = Field(..., min_length=3, max_length=50, description="Unique username")
    full_name: str = Field(..., min_length=1, max_length=100, description="User full name")
    
    # Authentication
    hashed_password: str = Field(..., description="Hashed password")
    is_active: bool = Field(default=True, description="Whether user is active")
    is_verified: bool = Field(default=False, description="Whether email is verified")
    
    # Profile information
    avatar_url: Optional[str] = Field(default=None, description="Profile avatar URL")
    bio: Optional[str] = Field(default=None, max_length=500, description="User biography")
    location: Optional[str] = Field(default=None, max_length=100, description="User location")
    
    # Timestamps
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    email_verified_at: Optional[datetime] = Field(default=None, description="Email verification timestamp")
    
    # Metadata
    login_count: int = Field(default=0, description="Number of logins")
    roles: List[str] = Field(default_factory=list, description="User roles")
    tags: List[str] = Field(default_factory=list, description="User tags for categorization")
    
    class Settings:
        collection = "users"
        indexes = [
            # Compound index for email and active status
            IndexModel([("email", ASCENDING), ("is_active", ASCENDING)]),
            
            # Text search index for full name and bio
            IndexModel([("full_name", TEXT), ("bio", TEXT)]),
            
            # Index for filtering by roles
            IndexModel([("roles", ASCENDING)]),
            
            # Index for last login queries
            IndexModel([("last_login", ASCENDING)]),
            
            # Compound index for active verified users
            IndexModel([("is_active", ASCENDING), ("is_verified", ASCENDING)]),
            
            # Index for location-based queries
            IndexModel([("location", ASCENDING)]),
            
            # Index for tags
            IndexModel([("tags", ASCENDING)])
        ]
