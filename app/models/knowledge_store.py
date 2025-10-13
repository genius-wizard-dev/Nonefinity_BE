from typing import Optional
from beanie import Document
from pydantic import Field
from app.models.time_mixin import TimeMixin
from pymongo import IndexModel

class KnowledgeStore(TimeMixin, Document):
    name: str = Field(..., description="Knowledge store name")
    description: Optional[str] = Field(None, description="Knowledge store description")
    owner_id: str = Field(..., description="Owner ID")
    collection_name: str = Field(..., description="Collection name")
    dimension: int = Field(..., description="Dimension")
    distance: str = Field(..., description="Distance")

    class Settings:
        name = "knowledge_stores"
        indexes = [
            IndexModel([("owner_id", 1), ("name", 1)], unique=True),
        ]
