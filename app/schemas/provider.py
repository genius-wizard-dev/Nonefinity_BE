from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class ProviderResponse(BaseModel):
    """Enhanced response schema for Provider with full configuration support"""
    id: str
    provider: str
    name: str
    description: Optional[str] = None
    base_url: str
    logo_url: Optional[str] = None
    docs_url: Optional[str] = None
    models_url: Optional[str] = None
    api_key_header: str
    api_key_prefix: str
    is_active: bool
    support: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProviderTaskConfigResponse(BaseModel):
    """Response schema for provider task configuration"""
    task_type: str
    class_path: str
    init_params: List[str]
    provider: str


class ProviderDetailResponse(ProviderResponse):
    """Detailed provider response with task configurations"""
    available_tasks: List[str] = Field(default_factory=list)

    @validator('available_tasks', pre=True, always=True)
    def set_available_tasks(cls, v, values):
        """Set available tasks from support field"""
        return values.get('support', [])


class ProviderList(BaseModel):
    """Schema for provider list response"""
    providers: List[ProviderResponse]
    total: int


