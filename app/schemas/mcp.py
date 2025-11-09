from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class MCPConfigBase(BaseModel):
    """Base schema for MCP config"""
    transport: str = Field(..., description="Transport type: stdio or streamable_http")
    command: Optional[str] = Field(None, description="Command for stdio transport")
    args: Optional[List[str]] = Field(None, description="Arguments for stdio transport")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables (optional)")

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Validate transport type"""
        if v not in ["stdio", "streamable_http"]:
            raise ValueError("Transport must be either 'stdio' or 'streamable_http'")
        return v

    @field_validator("command", "args")
    @classmethod
    def validate_stdio_fields(cls, v, info):
        """Validate stdio fields are present when transport is stdio"""
        if info.data.get("transport") == "stdio":
            if info.field_name == "command" and not v:
                raise ValueError("Command is required when transport is 'stdio'")
            if info.field_name == "args" and not v:
                raise ValueError("Args is required when transport is 'stdio'")
        return v


class MCPCreateRequest(BaseModel):
    """Request model for creating MCP config"""
    name: str = Field(..., description="Display name for MCP configuration (different from server name)")
    description: Optional[str] = Field(default=None, description="Description of the MCP configuration")
    config: Dict[str, Any] = Field(..., description="MCP server configuration as JSON object")

    @field_validator("config")
    @classmethod
    def validate_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate config structure"""
        if not v:
            raise ValueError("Config cannot be empty")

        # Config should be a dict with server name as key
        if len(v) != 1:
            raise ValueError("Config must contain exactly one server configuration")

        server_name = list(v.keys())[0]

        # Validate server name: only lowercase letters, numbers, and hyphens
        import re
        if not re.match(r'^[a-z0-9-]+$', server_name):
            raise ValueError("Server name must contain only lowercase letters, numbers, and hyphens")

        server_config = v[server_name]

        if not isinstance(server_config, dict):
            raise ValueError("Server configuration must be a dictionary")

        # Validate transport
        transport = server_config.get("transport")
        if transport not in ["stdio", "streamable_http"]:
            raise ValueError("Transport must be either 'stdio' or 'streamable_http'")

        # Validate transport-specific fields
        if transport == "stdio":
            if not server_config.get("command"):
                raise ValueError("Command is required when transport is 'stdio'")
            if not server_config.get("args"):
                raise ValueError("Args is required when transport is 'stdio'")
        elif transport == "streamable_http":
            if not server_config.get("url"):
                raise ValueError("URL is required when transport is 'streamable_http'")

        return v


class MCPUpdateRequest(BaseModel):
    """Request model for updating MCP config"""
    name: Optional[str] = Field(None, description="Display name for MCP configuration (different from server name)")
    description: Optional[str] = Field(None, description="Description of the MCP configuration")
    config: Optional[Dict[str, Any]] = Field(None, description="MCP server configuration as JSON object")


class MCPResponse(BaseModel):
    """Schema for MCP response"""
    id: str = Field(..., description="MCP ID")
    owner_id: str = Field(..., description="Owner ID (user ID)")
    name: str = Field(..., description="Display name for MCP configuration")
    description: Optional[str] = Field(None, description="Description of the MCP configuration")
    server_name: str = Field(..., description="MCP server name (extracted from config)")
    transport: str = Field(..., description="Transport type (extracted from config)")
    config: Dict[str, Any] = Field(..., description="MCP configuration as JSON")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="List of tools from MCP server")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class MCPListItemResponse(BaseModel):
    """Schema for MCP list item response"""
    id: str = Field(..., description="MCP ID")
    name: str = Field(..., description="Display name for MCP configuration")
    description: Optional[str] = Field(None, description="Description of the MCP configuration")
    server_name: str = Field(..., description="MCP server name (extracted from config)")
    transport: str = Field(..., description="Transport type (extracted from config)")
    tools_count: int = Field(..., description="Number of tools available")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

