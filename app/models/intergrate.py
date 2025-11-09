from typing import List, Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field

from app.models.time_mixin import TimeMixin


class Integration(TimeMixin, Document):
    """Integration model to track user's connected Composio integrations and their tool configurations"""
    user_id: str = Field(..., description="User ID from our system")
    auth_config_id: str = Field(..., description="Auth config ID from Composio")
    auth_config_name: str = Field(..., description="Auth config name from Composio")
    logo: str = Field(default="", description="Auth config logo from Composio")
    toolkit_slug: Optional[str] = Field(default=None, description="Toolkit slug from Composio")
    list_tools_slug: List[str] = Field(default_factory=list, description="List of tools from Composio")

    class Settings:
        name = "integrations"
        indexes = [
            [("user_id", 1)],  # Index on user_id for faster queries
            [("user_id", 1), ("auth_config_id", 1)],  # Compound index for unique user+config queries
            [("user_id", 1), ("toolkit_slug", 1)],  # Compound index for toolkit queries
        ]
