from typing import Optional, Dict, Any, List
from beanie import Document
from pydantic import Field

from app.models.time_mixin import TimeMixin


class MCP(TimeMixin, Document):
    """MCP (Model Context Protocol) model to store MCP server configurations"""
    owner_id: str = Field(..., description="Owner ID (user ID) from our system")
    name: str = Field(..., description="Display name for MCP configuration (different from server name)")
    description: Optional[str] = Field(default=None, description="Description of the MCP configuration")
    config: Dict[str, Any] = Field(..., description="MCP server configuration as JSON")
    tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of tools from MCP server as JSON")

    class Settings:
        name = "mcps"
        indexes = [
            [("owner_id", 1)],  # Index on owner_id for faster queries
        ]

    @property
    def server_name(self) -> str:
        """Extract server name from config"""
        if self.config and len(self.config) == 1:
            return list(self.config.keys())[0]
        return ""

    @property
    def transport(self) -> str:
        """Extract transport from config"""
        if self.config and len(self.config) == 1:
            server_config = list(self.config.values())[0]
            if isinstance(server_config, dict):
                return server_config.get("transport", "stdio")
        return "stdio"

