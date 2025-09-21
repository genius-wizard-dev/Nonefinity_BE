"""
Schemas for embedding API endpoints
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, validator


class EmbeddingRequest(BaseModel):
    """Schema for embedding request"""

    user_id: str = Field(..., description="User identifier")
    file_id: str = Field(..., description="File identifier")
    chunks: List[str] = Field(..., description="List of text chunks to embed", min_items=1)
    split_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration for text splitting"
    )
    provider: str = Field(..., description="AI provider (e.g., 'openai')")
    model_id: str = Field(..., description="Model identifier")
    credential: Dict[str, str] = Field(..., description="Provider credentials")

    @validator('chunks')
    def validate_chunks(cls, v):
        if not v:
            raise ValueError("At least one chunk is required")
        return v

    @validator('provider')
    def validate_provider(cls, v):
        if v.lower() not in ['openai']:
            raise ValueError("Only 'openai' provider is currently supported")
        return v.lower()

    @validator('credential')
    def validate_credential(cls, v, values):
        provider = values.get('provider', '').lower()
        if provider == 'openai':
            if 'api_key' not in v or not v['api_key']:
                raise ValueError("API key is required for OpenAI provider")
        return v


class BatchEmbeddingRequest(BaseModel):
    """Schema for batch embedding request"""

    batch_requests: List[EmbeddingRequest] = Field(
        ...,
        description="List of embedding requests",
        min_items=1,
        max_items=100
    )

    @validator('batch_requests')
    def validate_batch_requests(cls, v):
        if len(v) > 100:
            raise ValueError("Maximum 100 requests per batch")
        return v


class TaskResponse(BaseModel):
    """Schema for task submission response"""

    success: bool = Field(..., description="Whether the task was submitted successfully")
    task_id: str = Field(..., description="Celery task identifier")
    message: str = Field(..., description="Response message")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )


class TaskStatusResponse(BaseModel):
    """Schema for task status response"""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status")
    ready: bool = Field(..., description="Whether task is ready")
    successful: Optional[bool] = Field(default=None, description="Whether task was successful")
    failed: Optional[bool] = Field(default=None, description="Whether task failed")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result if available")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    meta: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None,
        description="Additional task metadata"
    )


class TaskResultResponse(BaseModel):
    """Schema for task result response"""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status")
    ready: bool = Field(..., description="Whether task is ready")
    successful: Optional[bool] = Field(default=None, description="Whether task was successful")
    failed: Optional[bool] = Field(default=None, description="Whether task failed")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class EmbeddingResult(BaseModel):
    """Schema for embedding result data"""

    user_id: str = Field(..., description="User identifier")
    file_id: str = Field(..., description="File identifier")
    provider: str = Field(..., description="AI provider used")
    model_id: str = Field(..., description="Model identifier used")
    total_chunks: int = Field(..., description="Total number of chunks processed")
    successful_chunks: int = Field(..., description="Number of successfully processed chunks")
    split_config: Dict[str, Any] = Field(..., description="Split configuration used")
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    chunks: List[str] = Field(..., description="Original text chunks")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")


class ActiveTasksResponse(BaseModel):
    """Schema for active tasks response"""

    active_tasks: Dict[str, Any] = Field(..., description="Active tasks by worker")
    total_active: int = Field(..., description="Total number of active tasks")
    workers: Optional[List[str]] = Field(default=None, description="List of worker names")
    message: Optional[str] = Field(default=None, description="Additional message")
    error: Optional[str] = Field(default=None, description="Error message if any")


class TaskCancelResponse(BaseModel):
    """Schema for task cancellation response"""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Cancellation status")
    message: Optional[str] = Field(default=None, description="Cancellation message")
    error: Optional[str] = Field(default=None, description="Error message if failed")
