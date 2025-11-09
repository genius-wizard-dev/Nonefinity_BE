from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class IntegrationBase(BaseModel):
    """Base schema for Integration"""
    auth_config_id: str = Field(..., description="Auth config ID from Composio")
    auth_config_name: str = Field(..., description="Auth config name from Composio")
    logo: str = Field(default="", description="Auth config logo from Composio")
    toolkit_slug: Optional[str] = Field(default=None, description="Toolkit slug from Composio")
    list_tools_slug: List[str] = Field(default_factory=list, description="List of tools from Composio")


class IntegrationCreate(IntegrationBase):
    """Schema for creating integration"""
    pass


class IntegrationUpdate(BaseModel):
    """Schema for updating integration"""
    auth_config_name: Optional[str] = Field(None, description="Auth config name from Composio")
    logo: Optional[str] = Field(None, description="Auth config logo from Composio")
    toolkit_slug: Optional[str] = Field(None, description="Toolkit slug from Composio")
    list_tools_slug: Optional[List[str]] = Field(None, description="List of tools from Composio")


class IntegrationResponse(IntegrationBase):
    """Schema for integration response"""
    id: str = Field(..., description="Integration ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class ConfigItemSchema(BaseModel):
    """Config item schema with id, name, toolkit_slug, logo and tools (for backward compatibility)"""
    id: str = Field(..., description="Auth config ID from Composio")
    name: str = Field(..., description="Auth config name from Composio")
    logo: str = Field(..., description="Auth config logo from Composio")
    toolkit_slug: Optional[str] = Field(default=None, description="Toolkit slug from Composio")
    list_tools_slug: List[str] = Field(default_factory=list, description="List of tools from Composio")


class IntegrationItemResponse(BaseModel):
    """Schema for integration item in list response with is_login status"""
    id: str = Field(..., description="Auth config ID")
    name: str = Field(..., description="Auth config name")
    status: str = Field(..., description="Status (ENABLED/DISABLED)")
    toolkit: dict = Field(..., description="Toolkit information")
    is_login: bool = Field(..., description="Whether user has connected this integration")


class IntegrationListResponse(BaseModel):
    """Schema for integration list response"""
    current_page: float = Field(..., description="Current page number")
    items: List[IntegrationItemResponse] = Field(..., description="List of integrations")
    total_items: float = Field(..., description="Total number of items")
    total_pages: float = Field(..., description="Total number of pages")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page")


class AddToolsRequest(BaseModel):
    """Request model for adding tools"""
    tool_slugs: List[str] = Field(..., description="List of tool slugs to add")


class ConnectAccountRequest(BaseModel):
    """Request model for connecting an account"""
    auth_config_id: str = Field(..., description="The authentication configuration ID from Composio")
