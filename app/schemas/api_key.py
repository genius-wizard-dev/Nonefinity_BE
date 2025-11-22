"""API Key Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """Schema for creating an API key"""
    name: str = Field(..., description="Friendly name for the API key",
                      min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(
        30,
        description="Number of days until expiration (1-30 days, default 30)",
        ge=1,
        le=30,
    )


class APIKeyResponse(BaseModel):
    """Schema for API key response"""
    id: str
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes the actual key)"""
    api_key: str = Field(
        ..., description="The actual API key - save this securely, it won't be shown again")


class APIKeyListResponse(BaseModel):
    """Schema for listing API keys"""
    api_keys: list[APIKeyResponse]
    total: int
    skip: int
    limit: int


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key"""
    name: Optional[str] = Field(None, description="New name for the API key")
    is_active: Optional[bool] = Field(
        None, description="Activate or deactivate the key")
