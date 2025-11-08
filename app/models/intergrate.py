from typing import List, Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field

from app.models.time_mixin import TimeMixin


class ConfigItem(BaseModel):
    """Config item with id, name, toolkit_slug and list of tools"""
    id: str = Field(..., description="Auth config ID from Composio")
    name: str = Field(..., description="Auth config name from Composio")
    logo: str = Field(..., description="Auth config logo from Composio")
    toolkit_slug: Optional[str] = Field(default=None, description="Toolkit slug from Composio")
    list_tools_slug: List[str] = Field(default_factory=list, description="List of tools from Composio")


class Integration(TimeMixin, Document):
    """Integration model to track user's connected Composio integrations"""
    user_id: str = Field(..., description="User ID from our system")
    configs: List[ConfigItem] = Field(default_factory=list, description="List of connected configs with id, name, toolkit_slug and tools")


    class Settings:
        name = "integrations"
        indexes = [
            [("user_id", 1)],  # Index on user_id for faster queries
        ]

