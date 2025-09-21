from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class CredentialBase(BaseModel):
    """Base schema for Credential"""
    name: str = Field(..., min_length=1, max_length=100, description="Credential name")
    provider_name: str = Field(..., description="AI provider identifier")
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


class CredentialCreate(CredentialBase):
    """Schema for creating credential"""
    pass


class CredentialUpdate(BaseModel):
    """Schema for updating credential"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Credential name")
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
    id: str
    name: str
    provider_name: str
    base_url: Optional[str] = None
    additional_headers: Optional[Dict[str, str]] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CredentialDetail(Credential):
    """Detailed credential response with masked API key"""
    api_key_masked: str


class CredentialList(BaseModel):
    """Schema for credential list response"""
    credentials: List[Credential]
    total: int
    page: int
    size: int


class ProviderResponse(BaseModel):
    """Response schema for Provider - simplified"""
    id: str
    provider_name: str
    name: str
    base_url: str
    api_key_header: str
    api_key_prefix: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProviderList(BaseModel):
    """Schema for provider list response"""
    providers: List[ProviderResponse]
    total: int


class CredentialTestRequest(BaseModel):
    """Request schema for testing a credential"""
    credential_id: Optional[str] = Field(None, description="Credential ID to test")
    provider_name: Optional[str] = Field(None, description="Provider name for ad-hoc testing")
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


class SecureKeyResponse(BaseModel):
    """Response schema for secure key generation"""
    secure_key: str
    length: int
    timestamp: str
    recommendation: str
