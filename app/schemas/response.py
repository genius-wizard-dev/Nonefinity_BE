from typing import Generic, List, Optional, TypeVar
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


T = TypeVar("T")

class Pagination(BaseModel):
    """Pagination metadata for paginated responses"""
    total: int = Field(..., ge=0, description="Total number of items across all pages")
    page: int = Field(..., ge=1, description="Current page number (1-based)")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    pages: int = Field(..., ge=1, description="Total number of pages")
    next: Optional[str] = Field(None, description="URL for next page (if available)")
    previous: Optional[str] = Field(None, description="URL for previous page (if available)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 150,
                "page": 2,
                "page_size": 50,
                "pages": 3,
                "next": "/api/v1/files?page=3&limit=50",
                "previous": "/api/v1/files?page=1&limit=50"
            }
        }
    )

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper for all endpoints"""
    success: bool = Field(True, description="Indicates if the request was successful")
    message: Optional[str] = Field(None, description="Human-readable message about the operation")
    data: Optional[T] = Field(None, description="Response data payload")
    meta: Optional[Pagination] = Field(None, description="Pagination metadata (for paginated responses)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": "123", "name": "example"},
                "meta": None
            }
        }
    )

class ErrorDetail(BaseModel):
    """Detailed error information for validation and business logic errors"""
    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field name that caused the error (for validation errors)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "File name is required",
                "field": "file_name"
            }
        }
    )

class ApiError(BaseModel):
    """Error response wrapper for failed operations"""
    success: bool = Field(False, description="Always false for error responses")
    message: str = Field(..., description="Main error message")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "message": "Validation failed",
                "errors": [
                    {
                        "code": "REQUIRED_FIELD",
                        "message": "File name is required",
                        "field": "file_name"
                    }
                ],
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    )

class HealthCheck(BaseModel):
    """Health check response schema"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: Optional[str] = Field(None, description="API version")
    uptime: Optional[float] = Field(None, description="Service uptime in seconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "1.0.0",
                "uptime": 3600.5
            }
        }
    )
