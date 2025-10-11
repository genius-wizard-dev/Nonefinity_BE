from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator, ConfigDict


class CredentialBase(BaseModel):
    """Base schema for Credential"""
    name: str = Field(..., min_length=1, max_length=100, description="Credential name")
    provider_id: str = Field(..., description="AI provider ID")
    api_key: str = Field(..., min_length=1, description="API key")
    base_url: Optional[str] = Field(None, description="Custom base URL (overrides provider default)")
    additional_headers: Optional[Dict[str, str]] = Field(None, description="Additional headers for API calls")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty or whitespace only')
        return v.strip()

    @validator('api_key')
    def api_key_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('API key cannot be empty or whitespace only')
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "OpenAI Production Key",
                "provider_id": "openai",
                "api_key": "sk-1234567890abcdef",
                "base_url": "https://api.openai.com/v1",
                "additional_headers": {
                    "Organization": "org-123"
                }
            }
        }
    )


class CredentialCreate(CredentialBase):
    """Schema for creating credential"""
    pass


class CredentialUpdate(BaseModel):
    """Schema for updating credential"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Credential name")
    provider_id: Optional[str] = Field(None, description="AI provider ID")
    api_key: Optional[str] = Field(None, min_length=1, description="API key")
    base_url: Optional[str] = Field(None, description="Custom base URL")
    additional_headers: Optional[Dict[str, str]] = Field(None, description="Additional headers for API calls")
    is_active: Optional[bool] = Field(None, description="Whether the credential is active")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty or whitespace only')
        return v.strip() if v else v

    @validator('api_key')
    def api_key_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError('API key cannot be empty or whitespace only')
        return v.strip() if v else v


class Credential(BaseModel):
    """Schema for Credential response"""
    id: str = Field(..., description="Unique credential identifier")
    name: str = Field(..., description="Credential name")
    provider_id: str = Field(..., description="AI provider ID")
    provider_name: Optional[str] = Field(None, description="Human-readable provider name")
    base_url: Optional[str] = Field(None, description="Custom base URL")
    additional_headers: Optional[Dict[str, str]] = Field(None, description="Additional headers for API calls")
    is_active: bool = Field(..., description="Whether the credential is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "OpenAI Production Key",
                "provider_id": "openai",
                "provider_name": "OpenAI",
                "base_url": "https://api.openai.com/v1",
                "additional_headers": {
                    "Organization": "org-123"
                },
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class CredentialDetail(Credential):
    """Detailed credential response with masked API key"""
    api_key: str = Field(..., description="Masked API key for display")
    usage_count: Optional[int] = Field(None, description="Number of times this credential is used")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "OpenAI Production Key",
                "provider_id": "openai",
                "provider_name": "OpenAI",
                "api_key": "sk-***masked***",
                "base_url": "https://api.openai.com/v1",
                "additional_headers": {
                    "Organization": "org-123"
                },
                "is_active": True,
                "usage_count": 150,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class CredentialList(BaseModel):
    """Schema for credential list response"""
    credentials: List[CredentialDetail] = Field(..., description="List of credentials")
    total: int = Field(..., ge=0, description="Total number of credentials")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Number of items per page")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "credentials": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "name": "OpenAI Production Key",
                        "provider_id": "openai",
                        "api_key": "sk-***masked***",
                        "is_active": True,
                        "usage_count": 150
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 100
            }
        }
    )


class CredentialTestRequest(BaseModel):
    """Request schema for testing a credential"""
    credential_id: Optional[str] = Field(None, description="Credential ID to test")
    provider: Optional[str] = Field(None, description="Provider name for ad-hoc testing")
    api_key: Optional[str] = Field(None, description="API key for ad-hoc testing")
    base_url: Optional[str] = Field(None, description="Custom base URL for testing")


class CredentialTestResponse(BaseModel):
    """Response schema for credential test"""
    is_valid: bool
    message: str
    response_time_ms: Optional[int] = None
    error_details: Optional[str] = None


class EncryptionHealthResponse(BaseModel):
    """Response schema for encryption health check"""
    encryption_healthy: bool
    test_passed: bool
    encryption_algorithm: Optional[str] = None
    kdf_iterations: Optional[int] = None
    timestamp: str
    error: Optional[str] = None


class SecureKeyRequest(BaseModel):
    """Request schema for secure key generation"""
    length: int = Field(default=32, ge=16, le=128, description="Key length in bytes")

class SecureKeyResponse(BaseModel):
    """Response schema for secure key generation"""
    secure_key: str
    length: int
    timestamp: str
    recommendation: str
