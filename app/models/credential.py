from typing import Annotated, Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel

from app.models.time_mixin import TimeMixin
from app.models.soft_delete_mixin import SoftDeleteMixin


class Provider(TimeMixin, Document):
    """Provider model - simplified version"""
    provider_name: Annotated[str, Indexed(unique=True)] = Field(..., description="Unique provider identifier")
    name: str = Field(..., description="Display name")
    base_url: str = Field(..., description="API base URL")
    api_key_header: str = Field(default="Authorization", description="Header for API key")
    api_key_prefix: str = Field(default="Bearer", description="Prefix for API key")
    is_active: bool = Field(default=True, description="Is provider active")

    class Settings:
        name = "providers"


class Credential(TimeMixin, SoftDeleteMixin, Document):
    """User credential model for AI providers"""
    owner_id: Annotated[str, Indexed()] = Field(..., description="Owner ID from authentication")
    name: str = Field(..., min_length=1, max_length=100, description="Credential name")
    provider_name: Annotated[str, Indexed()] = Field(..., description="AI provider identifier")
    api_key: str = Field(..., description="Encrypted API key")
    base_url: Optional[str] = Field(None, description="Custom base URL (overrides provider default)")
    additional_headers: Optional[dict] = Field(default=None, description="Additional headers for API calls")
    is_active: bool = Field(default=True, description="Whether the credential is active")

    class Settings:
        name = "credentials"
        indexes = [
            IndexModel([("owner_id", 1), ("name", 1)], unique=True),
            IndexModel([("owner_id", 1), ("provider_name", 1)]),
            IndexModel([("owner_id", 1), ("is_deleted", 1)])
        ]
