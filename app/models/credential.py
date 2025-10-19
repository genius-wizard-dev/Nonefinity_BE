from typing import Annotated, Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel
from bson import ObjectId

from app.models.time_mixin import TimeMixin
from app.models.provider import Provider


class Credential(TimeMixin, Document):
    """User credential model for AI providers"""
    owner_id: Annotated[str, Indexed()] = Field(..., description="Owner ID from authentication")
    name: str = Field(..., min_length=1, max_length=100, description="Credential name")
    provider_id: Annotated[str, Indexed()] = Field(..., description="AI provider ID")
    api_key: str = Field(..., description="Encrypted API key")
    base_url: Optional[str] = Field(None, description="Custom base URL (overrides provider default)")
    additional_headers: Optional[dict] = Field(default=None, description="Additional headers for API calls")
    is_active: bool = Field(default=True, description="Whether the credential is active")

    async def get_provider(self) -> Optional[Provider]:
        """Get the associated provider for this credential"""
        return await Provider.find_one(
            Provider.id == ObjectId(self.provider_id),
            Provider.is_active == True
        )

    class Settings:
        name = "credentials"
        indexes = [
            IndexModel([("owner_id", 1), ("name", 1)], unique=True),
            IndexModel([("owner_id", 1), ("provider_id", 1)]),
            IndexModel([("owner_id", 1), ("is_deleted", 1)])
        ]
