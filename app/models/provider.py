from typing import Annotated, Optional, List
from beanie import Document, Indexed
from pydantic import Field, validator
from pymongo import IndexModel

from app.models.time_mixin import TimeMixin


class ProviderTaskConfig(Document):
    """Configuration for provider tasks (embedding, chat, etc.)"""
    class_path: str = Field(..., description="Full class path for the LangChain implementation")
    init_params: List[str] = Field(default_factory=list, description="Required initialization parameters")

    class Settings:
        name = "provider_task_configs"


class Provider(TimeMixin, Document):
    """Enhanced Provider model optimized for MongoDB with full YAML configuration support"""

    # Basic identification
    provider: Annotated[str, Indexed(unique=True)] = Field(..., description="Unique provider identifier")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Provider description")

    # URLs and documentation
    base_url: str = Field(..., description="API base URL")
    logo_url: Optional[str] = Field(None, description="Provider logo URL")
    docs_url: Optional[str] = Field(None, description="Provider documentation URL")
    models_url: Optional[str] = Field(None, description="Provider models URL")
    # API configuration
    api_key_header: str = Field(default="Authorization", description="Header for API key")
    api_key_prefix: str = Field(default="Bearer", description="Prefix for API key")

    # Status and capabilities
    is_active: bool = Field(default=True, description="Is provider active")
    support: List[str] = Field(default_factory=list, description="Supported tasks (embedding, chat, moderation, etc.)")

    # Additional metadata for better querying
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    @validator('support')
    def validate_support(cls, v):
        """Validate supported task types"""
        valid_tasks = {'embedding', 'chat', 'moderation', 'completion', 'image', 'audio'}
        for task in v:
            if task not in valid_tasks:
                raise ValueError(f"Unsupported task type: {task}")
        return v


    class Settings:
        name = "providers"
        indexes = [
            IndexModel([("provider", 1)], unique=True),
            IndexModel([("is_active", 1)]),
            IndexModel([("support", 1)]),
            IndexModel([("tags", 1)]),
            IndexModel([("is_active", 1), ("support", 1)]),  # Compound index for common queries
        ]
