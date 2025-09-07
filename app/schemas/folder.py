from pydantic import BaseModel
from typing import Optional



class FolderCreate(BaseModel):
    """Internal schema for creating folder with all required fields"""
    owner_id: str
    folder_name: str
    folder_path: str
    parent_path: str = "/"

class FolderUpdate(BaseModel):
    """Schema for updating folder"""
    folder_name: Optional[str] = None
    parent_path: Optional[str] = None

class FolderResponse(BaseModel):
    """Schema for returning folder information"""
    id: str
    owner_id: str
    folder_name: str
    folder_path: str
    parent_path: str
    created_at: str
    updated_at: str
