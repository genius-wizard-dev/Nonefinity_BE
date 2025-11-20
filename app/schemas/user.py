from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    clerk_id: str = Field(..., description="Clerk user ID")
    emails: List[EmailStr] = Field(..., description="List of user email addresses")
    primary_email: EmailStr = Field(..., description="Primary email address")
    username: str = Field(..., description="Username")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    has_image: bool = Field(..., description="Whether user has profile image")
    profile_image: str = Field(..., description="Profile image URL")
    banned: bool = Field(..., description="Whether user is banned")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    is_oauth: bool = Field(..., description="Whether user signed up via OAuth")
    oauth_providers: Optional[List[str]] = Field(None, description="List of OAuth providers used")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "clerk_id": "user_2abc123def456",
                "emails": ["john@example.com"],
                "primary_email": "john@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "has_image": True,
                "profile_image": "https://img.clerk.com/...",
                "banned": False,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "is_oauth": True,
                "oauth_providers": ["google"]
            }
        }
    )

class UserUpdate(BaseModel):
    """Schema for updating user information"""
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    username: Optional[str] = Field(None, description="Username")
    profile_image: Optional[str] = Field(None, description="Profile image URL")
    emails: List[EmailStr] = Field(..., description="List of user email addresses")
    primary_email: EmailStr = Field(..., description="Primary email address")
    oauth_providers: Optional[List[str]] = Field(default=[], description="List of OAuth providers used")
    has_image: bool = Field(default=False, description="Whether user has profile image")
    banned: bool = Field(default=False, description="Whether user is banned")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "profile_image": "https://img.clerk.com/...",
                "emails": ["john@example.com"],
                "primary_email": "john@example.com",
                "oauth_providers": ["google"],
                "has_image": True,
                "banned": False,
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )

class UserResponse(BaseModel):
    """Schema for user response"""
    clerk_id: str = Field(..., description="Clerk user ID")
    emails: List[EmailStr] = Field(..., description="List of user email addresses")
    primary_email: EmailStr = Field(..., description="Primary email address")
    username: str = Field(..., description="Username")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    has_image: bool = Field(..., description="Whether user has profile image")
    profile_image: str = Field(..., description="Profile image URL")
    banned: bool = Field(..., description="Whether user is banned")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    is_oauth: bool = Field(..., description="Whether user signed up via OAuth")
    oauth_providers: Optional[List[str]] = Field(None, description="List of OAuth providers used")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "clerk_id": "user_2abc123def456",
                "emails": ["john@example.com"],
                "primary_email": "john@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "has_image": True,
                "profile_image": "https://img.clerk.com/...",
                "banned": False,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "is_oauth": True,
                "oauth_providers": ["google"]
            }
        }
    )
