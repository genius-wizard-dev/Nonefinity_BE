from typing import Annotated, Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel
from enum import Enum
from bson import ObjectId
from app.models.time_mixin import TimeMixin
from app.models.credential import Credential


class ModelType(str, Enum):
    """AI model types"""
    CHAT = "chat"
    EMBEDDING = "embedding"


class Model(TimeMixin, Document):
    """AI Model configuration for users"""
    owner_id: Annotated[str, Indexed()] = Field(..., description="Owner ID from authentication")
    credential_id: Annotated[str, Indexed()] = Field(..., description="Associated credential ID")
    name: str = Field(..., min_length=1, max_length=100, description="Model display name")
    model: str = Field(..., min_length=1, description="AI model identifier (e.g., gpt-4, text-embedding-ada-002)")
    type: ModelType = Field(..., description="Model type (chat or embedding)")
    description: Optional[str] = Field(None, max_length=500, description="Model description")
    is_active: bool = Field(default=True, description="Whether the model is active")
    dimension: Optional[int] = Field(None, description="Embedding dimension (only present if type is embedding)")

    async def get_credential(self) -> Optional[Credential]:
        """Get the associated credential for this model"""
        return await Credential.find_one(
            Credential.id == ObjectId(self.credential_id) ,
            Credential.owner_id == self.owner_id,
            Credential.is_active == True
        )

    class Settings:
        name = "models"
        indexes = [
            IndexModel([("owner_id", 1), ("name", 1)], unique=True),
            IndexModel([("owner_id", 1), ("type", 1)]),
            IndexModel([("owner_id", 1), ("credential_id", 1)]),
        ]
