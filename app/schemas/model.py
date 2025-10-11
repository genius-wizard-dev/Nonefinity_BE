from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.model import ModelType


class ModelCreate(BaseModel):
    """Schema for creating a new AI model"""
    credential_id: str = Field(..., description="Associated credential ID")
    name: str = Field(..., min_length=1, max_length=100, description="Model display name")
    model: str = Field(..., min_length=1, description="AI model identifier")
    type: ModelType = Field(..., description="Model type (chat or embedding)")
    description: Optional[str] = Field(None, max_length=500, description="Model description")
    is_active: bool = Field(default=True, description="Whether the model is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "credential_id": "507f1f77bcf86cd799439011",
                "name": "GPT-4 Chat Model",
                "model": "gpt-4",
                "type": "chat",
                "description": "OpenAI GPT-4 model for chat completions",
                "is_active": True
            }
        }
    )


class ModelUpdate(BaseModel):
    """Schema for updating an AI model"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Model display name")
    description: Optional[str] = Field(None, max_length=500, description="Model description")
    is_active: Optional[bool] = Field(None, description="Whether the model is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated GPT-4 Chat Model",
                "description": "Updated description for GPT-4 model",
                "is_active": False
            }
        }
    )


class ModelResponse(BaseModel):
    """Schema for AI model response"""
    id: str = Field(..., description="Unique model identifier")
    owner_id: str = Field(..., description="Owner ID")
    credential_id: str = Field(..., description="Associated credential ID")
    name: str = Field(..., description="Model display name")
    model: str = Field(..., description="AI model identifier")
    type: ModelType = Field(..., description="Model type")
    description: Optional[str] = Field(None, description="Model description")
    is_active: bool = Field(..., description="Whether the model is active")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "owner_id": "507f1f77bcf86cd799439012",
                "credential_id": "507f1f77bcf86cd799439013",
                "name": "GPT-4 Chat Model",
                "model": "gpt-4",
                "type": "chat",
                "description": "OpenAI GPT-4 model for chat completions",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class ModelListResponse(BaseModel):
    """Schema for listing AI models"""
    models: list[ModelResponse] = Field(..., description="List of models")
    total: int = Field(..., ge=0, description="Total number of models")
    skip: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Number of items per page")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "models": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "owner_id": "507f1f77bcf86cd799439012",
                        "credential_id": "507f1f77bcf86cd799439013",
                        "name": "GPT-4 Chat Model",
                        "model": "gpt-4",
                        "type": "chat",
                        "description": "OpenAI GPT-4 model",
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 50
            }
        }
    )


class ModelStats(BaseModel):
    """Schema for model statistics"""
    total_models: int = Field(..., ge=0, description="Total number of models")
    chat_models: int = Field(..., ge=0, description="Number of chat models")
    embedding_models: int = Field(..., ge=0, description="Number of embedding models")
    active_models: int = Field(..., ge=0, description="Number of active models")
    inactive_models: int = Field(..., ge=0, description="Number of inactive models")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_models": 10,
                "chat_models": 6,
                "embedding_models": 4,
                "active_models": 8,
                "inactive_models": 2
            }
        }
    )

class ModelCreateRequest(BaseModel):
    """Request schema for creating model via JSON"""
    credential_id: str = Field(..., description="Associated credential ID")
    name: str = Field(..., min_length=1, max_length=100, description="Model display name")
    model: str = Field(..., min_length=1, description="AI model identifier")
    type: ModelType = Field(..., description="Model type (chat or embedding)")
    description: Optional[str] = Field(None, max_length=500, description="Model description")
    is_active: bool = Field(default=True, description="Whether the model is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "credential_id": "507f1f77bcf86cd799439011",
                "name": "GPT-4 Chat Model",
                "model": "gpt-4",
                "type": "chat",
                "description": "OpenAI GPT-4 model for chat completions",
                "is_active": True
            }
        }
    )

class ModelUpdateRequest(BaseModel):
    """Request schema for updating model via JSON"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Model display name")
    description: Optional[str] = Field(None, max_length=500, description="Model description")
    is_active: Optional[bool] = Field(None, description="Whether the model is active")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated GPT-4 Chat Model",
                "description": "Updated description for GPT-4 model",
                "is_active": False
            }
        }
    )
