"""API Key Schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """Schema for creating an API key"""
    name: str = Field(..., description="Friendly name for the API key", min_length=1, max_length=100)
    chat_config_id: Optional[str] = Field(None, description="Chat config ID to scope this key to (optional)")
    expires_in_days: Optional[int] = Field(None, description="Number of days until expiration (null for no expiration)", ge=1, le=365)
    permissions: list[str] = Field(default_factory=lambda: ["chat:read", "chat:write"], description="List of permissions")


class APIKeyResponse(BaseModel):
    """Schema for API key response"""
    id: str
    name: str
    chat_config_id: Optional[str] = None
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    permissions: list[str]
    created_at: datetime
    updated_at: datetime


class APIKeyCreateResponse(APIKeyResponse):
    """Schema for API key creation response (includes the actual key)"""
    api_key: str = Field(..., description="The actual API key - save this securely, it won't be shown again")


class APIKeyListResponse(BaseModel):
    """Schema for listing API keys"""
    api_keys: list[APIKeyResponse]
    total: int
    skip: int
    limit: int


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key"""
    name: Optional[str] = Field(None, description="New name for the API key")
    is_active: Optional[bool] = Field(None, description="Activate or deactivate the key")
    permissions: Optional[list[str]] = Field(None, description="Update permissions")
