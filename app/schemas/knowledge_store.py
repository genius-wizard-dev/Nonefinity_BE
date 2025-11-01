from typing import Optional
from pydantic import BaseModel, Field, field_validator
from qdrant_client.models import Distance
from enum import Enum
from datetime import datetime
from bson import ObjectId

class Dimension(int, Enum):
    DIMENSION_384 = 384
    DIMENSION_768 = 768
    DIMENSION_1024 = 1024
    DIMENSION_1536 = 1536
    DIMENSION_3072 = 3072




class KnowledgeStoreCreateRequest(BaseModel):
    name: str = Field(..., description="Knowledge store name")
    description: Optional[str] = Field(None, description="Knowledge store description")
    dimension: Dimension = Field(..., description="Dimension")
    distance: Distance = Field(..., description="Distance")


class KnowledgeStoreUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Knowledge store name")
    description: Optional[str] = Field(None, description="Knowledge store description")


class KnowledgeStoreResponse(BaseModel):
    id: str = Field(..., description="Knowledge store ID")
    name: str = Field(..., description="Knowledge store name")
    description: Optional[str] = Field(None, description="Knowledge store description")
    dimension: int = Field(..., description="Dimension")
    distance: str = Field(..., description="Distance")
    status: str = Field(..., description="Status")
    created_at: datetime = Field(..., description="Created at")
    updated_at: Optional[datetime] = Field(None, description="Updated at")
    points_count: int = Field(..., description="Point count")
    is_use: bool = Field(False, description="Whether this knowledge store is being used in chat configs")

    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_str(cls, v):
        """Convert ObjectId to string."""
        if isinstance(v, ObjectId):
            return str(v)
        return v

    @field_validator('updated_at', mode='before')
    @classmethod
    def handle_none_updated_at(cls, v):
        """Handle None updated_at values."""
        if v is None:
            return None
        return v

    class Config:
        from_attributes = True


class KnowledgeStoreListResponse(BaseModel):
    knowledge_stores: list[KnowledgeStoreResponse] = Field(..., description="List of knowledge stores")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Limit")
    skip: int = Field(..., description="Skip")


class ScrollDataRequest(BaseModel):
    limit: int = Field(5, ge=1, le=100, description="Number of points to return per scroll")
    scroll_id: Optional[str] = Field(None, description="Scroll ID for pagination")


class ScrollDataResponse(BaseModel):
    points: list[dict] = Field(..., description="List of points from Qdrant")
    scroll_id: Optional[str] = Field(None, description="Scroll ID for next page")
    has_more: bool = Field(..., description="Whether there are more points to scroll")
    total_scrolled: int = Field(..., description="Total number of points scrolled so far")


class DeleteVectorsRequest(BaseModel):
    point_ids: list[str] = Field(..., min_length=1, description="List of point IDs to delete")
