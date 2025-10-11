from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List, Dict
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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "owner_id": "507f1f77bcf86cd799439011",
                "bucket": "user-files",
                "file_path": "raw/507f1f77bcf86cd799439011/document.pdf",
                "file_name": "document",
                "file_ext": ".pdf",
                "file_type": "application/pdf",
                "file_size": 1024000
            }
        }
    )


class FileUpdate(BaseModel):
    """Schema for updating an existing file"""
    file_name: Optional[str] = Field(None, min_length=1, max_length=255, description="File name without extension")
    file_type: Optional[str] = Field(None, description="File MIME type")
    file_size: Optional[int] = Field(None, ge=0, description="File size (bytes)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_name": "updated_document",
                "file_type": "application/pdf",
                "file_size": 1024000
            }
        }
    )


class FileResponse(BaseModel):
    """Schema for returning file information"""
    id: str = Field(..., description="Unique file identifier")
    owner_id: str = Field(..., description="User/tenant who owns the file")
    bucket: str = Field(..., description="Bucket name in MinIO storage")
    file_path: str = Field(..., description="File path/ID in MinIO storage")
    file_name: str = Field(..., description="File name without extension")
    file_ext: str = Field(..., description="File extension")
    file_type: str = Field(..., description="File MIME type")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    created_at: datetime = Field(..., description="File creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "owner_id": "507f1f77bcf86cd799439012",
                "bucket": "user-files",
                "file_path": "raw/507f1f77bcf86cd799439012/document.pdf",
                "file_name": "document",
                "file_ext": ".pdf",
                "file_type": "application/pdf",
                "file_size": 1024000,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class BatchDeleteRequest(BaseModel):
    """Schema for batch delete request"""
    file_ids: List[str] = Field(..., min_items=1, max_items=100, description="List of file IDs to delete")

    @validator('file_ids')
    def validate_file_ids(cls, v):
        if not v:
            raise ValueError("At least one file ID is required")
        if len(v) > 100:
            raise ValueError("Maximum 100 files can be deleted at once")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_ids": [
                    "507f1f77bcf86cd799439011",
                    "507f1f77bcf86cd799439012",
                    "507f1f77bcf86cd799439013"
                ]
            }
        }
    )


class UploadUrlRequest(BaseModel):
    """Schema for upload URL request"""
    file_name: str = Field(..., min_length=1, max_length=255, description="Original file name")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    file_type: str = Field(..., description="File MIME type")

    @validator('file_name')
    def validate_file_name(cls, v):
        if not v.strip():
            raise ValueError("File name cannot be empty")
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_name": "my-document.pdf",
                "file_size": 1024000,
                "file_type": "application/pdf"
            }
        }
    )


class UploadUrlResponse(BaseModel):
    """Schema for upload URL response"""
    upload_url: str = Field(..., description="Presigned upload URL for direct file upload")
    object_name: str = Field(..., description="Object name in MinIO storage")
    expires_in: int = Field(..., description="URL expiry time in minutes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "upload_url": "https://minio.example.com/bucket/raw/user123/document.pdf?X-Amz-Algorithm=...",
                "object_name": "raw/user123/document.pdf",
                "expires_in": 60
            }
        }
    )


class FileMetadataRequest(BaseModel):
    """Schema for file metadata after upload"""
    object_name: str = Field(..., description="Object name in MinIO storage")
    file_name: str = Field(..., min_length=1, max_length=255, description="Original file name")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    file_type: str = Field(..., description="File MIME type")

    @validator('file_name')
    def validate_file_name(cls, v):
        if not v.strip():
            raise ValueError("File name cannot be empty")
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "object_name": "raw/user123/document.pdf",
                "file_name": "my-document.pdf",
                "file_size": 1024000,
                "file_type": "application/pdf"
            }
        }
    )


class FileStats(BaseModel):
    """Schema for file statistics response"""
    total_files: int = Field(..., ge=0, description="Total number of files")
    total_size: int = Field(..., ge=0, description="Total size in bytes")
    total_size_mb: float = Field(..., ge=0, description="Total size in megabytes")
    file_types: Dict[str, int] = Field(..., description="Count of files by type")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_files": 150,
                "total_size": 1073741824,
                "total_size_mb": 1024.0,
                "file_types": {
                    "application/pdf": 50,
                    "image/jpeg": 30,
                    "text/plain": 20,
                    "application/msword": 10
                }
            }
        }
    )


class FileSearchRequest(BaseModel):
    """Schema for file search request"""
    q: str = Field(..., min_length=1, description="Search query")
    file_type: Optional[str] = Field(None, description="Filter by file type")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results")

    @validator('q')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "q": "document",
                "file_type": "application/pdf",
                "limit": 20
            }
        }
    )
