from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.model import ModelType


class ModelCreate(BaseModel):
    """Schema for creating a new AI model"""
    credential_id: str = Field(..., description="Associated credential ID")
    name: str = Field(..., min_length=1, max_length=100, description="Model display name")
    model: str = Field(..., min_length=1, description="AI model identifier")
    type: ModelType = Field(..., description="Model type (chat or embedding)")
    description: Optional[str] = Field(None, max_length=500, description="Model description")
    is_active: bool = Field(default=True, description="Whether the model is active")
    is_default: bool = Field(default=False, description="Whether this is the default model for this type")


class ModelUpdate(BaseModel):
    """Schema for updating an AI model"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Model display name")
    description: Optional[str] = Field(None, max_length=500, description="Model description")
    is_active: Optional[bool] = Field(None, description="Whether the model is active")
    is_default: Optional[bool] = Field(None, description="Whether this is the default model for this type")


class ModelResponse(BaseModel):
    """Schema for AI model response"""
    id: str = Field(..., description="Model ID")
    owner_id: str = Field(..., description="Owner ID")
    credential_id: str = Field(..., description="Associated credential ID")
    name: str = Field(..., description="Model display name")
    model: str = Field(..., description="AI model identifier")
    type: ModelType = Field(..., description="Model type")
    description: Optional[str] = Field(None, description="Model description")
    is_active: bool = Field(..., description="Whether the model is active")
    is_default: bool = Field(..., description="Whether this is the default model for this type")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class ModelListResponse(BaseModel):
    """Schema for listing AI models"""
    models: list[ModelResponse] = Field(..., description="List of models")
    total: int = Field(..., description="Total number of models")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items per page")


class ModelStats(BaseModel):
    """Schema for model statistics"""
    total_models: int = Field(..., description="Total number of models")
    chat_models: int = Field(..., description="Number of chat models")
    embedding_models: int = Field(..., description="Number of embedding models")
    active_models: int = Field(..., description="Number of active models")
    inactive_models: int = Field(..., description="Number of inactive models")
