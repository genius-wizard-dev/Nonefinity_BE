from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FileCreate(BaseModel):
    """Schema for creating a new file (internal use with all fields)"""
    owner_id: str = Field(..., description="User/tenant who owns the file")
    bucket: str = Field(..., description="Bucket name in MinIO")
    file_path: str = Field(..., description="File path/ID in MinIO")
    file_name: str = Field(..., description="File name without extension")
    file_ext: str = Field(..., description="File extension")
    file_type: str = Field(..., description="File MIME type")
    file_size: Optional[int] = Field(None, description="File size (bytes)")
    url: Optional[str] = Field(None, description="Public URL to access the file")


class FileUpdate(BaseModel):
    """Schema for updating an existing file"""
    file_name: Optional[str] = Field(None, description="File name without extension")
    file_type: Optional[str] = Field(None, description="File MIME type")
    file_size: Optional[int] = Field(None, description="File size (bytes)")
    url: Optional[str] = Field(None, description="Public URL to access the file")


class FileResponse(BaseModel):
    """Schema for returning file information"""
    id: str = Field(..., description="File ID")
    owner_id: str = Field(..., description="User/tenant who owns the file")
    bucket: str = Field(..., description="Bucket name in MinIO")
    file_path: str = Field(..., description="File path/ID in MinIO")
    file_name: str = Field(..., description="File name without extension")
    file_ext: str = Field(..., description="File extension")
    file_type: str = Field(..., description="File MIME type")
    file_size: Optional[int] = Field(None, description="File size (bytes)")
    url: Optional[str] = Field(None, description="Public URL to access the file")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        from_attributes = True

