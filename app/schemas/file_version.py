from pydantic import BaseModel
from typing import Dict, Any, Optional


class FileVersionCreate(BaseModel):
    """Schema for creating a new file version"""
    version: int
    actions: Optional[Dict[str, Any]] = None
    source: str
    raw_id: str


class FileVersionUpdate(BaseModel):
    """Schema for updating an existing file version"""
    version: Optional[int] = None
    actions: Optional[Dict[str, Any]] = None
    source: Optional[str] = None


class FileVersionResponse(BaseModel):
    """Schema for returning file version information"""
    id: str
    version: int
    actions: Optional[Dict[str, Any]]
    source: str
    raw_id: str
    created_at: str
    updated_at: str
