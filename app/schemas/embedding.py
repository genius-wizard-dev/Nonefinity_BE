"""
Schemas for embedding API endpoints
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, validator, ConfigDict


class EmbeddingRequest(BaseModel):
    """Schema for embedding request"""
    file_id: str = Field(..., description="File identifier to process")
    model_id: Optional[str] = Field(None, description="Model identifier")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "507f1f77bcf86cd799439011",
                "model_id": "sentence-transformers/all-MiniLM-L6-v2"
            }
        }
    )


class SearchRequest(BaseModel):
    """Schema for similarity search request"""

    credential_id: Optional[str] = Field(
        default=None,
        description=(
            "Credential identifier for API key. Optional for 'huggingface'/'hf'/"
            "'local' providers using free open-source models."
        ),
    )
    query_text: str = Field(..., description="Text to search for", min_length=1, max_length=1000)
    provider: str = Field(
        default="huggingface", description="AI provider (e.g., 'huggingface', 'local', 'openai')")
    model_id: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", description="Model identifier")
    file_id: Optional[str] = Field(None, description="Optional filter by file")
    limit: int = Field(
        default=5, description="Number of results to return", ge=1, le=100)

    @validator('query_text')
    def validate_query_text(cls, v):
        if not v.strip():
            raise ValueError("Query text cannot be empty")
        return v.strip()

    @validator('provider')
    def validate_provider(cls, v):
        allowed = ['openai', 'huggingface', 'hf', 'local']
        if v.lower() not in allowed:
            raise ValueError(f"Provider must be one of {allowed}")
        return v.lower()

    @validator('credential_id')
    def validate_credential_with_provider(cls, v, values):
        provider = values.get('provider', 'huggingface')
        if provider not in ('huggingface', 'hf', 'local') and not v:
            raise ValueError(
                "credential_id is required for non-local providers")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "credential_id": "507f1f77bcf86cd799439011",
                "query_text": "machine learning algorithms",
                "provider": "huggingface",
                "model_id": "sentence-transformers/all-MiniLM-L6-v2",
                "file_id": "507f1f77bcf86cd799439012",
                "limit": 10
            }
        }
    )


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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "batch_requests": [
                    {
                        "file_id": "507f1f77bcf86cd799439011",
                        "model_id": "sentence-transformers/all-MiniLM-L6-v2"
                    },
                    {
                        "file_id": "507f1f77bcf86cd799439012",
                        "model_id": "sentence-transformers/all-MiniLM-L6-v2"
                    }
                ]
            }
        }
    )


class TaskResponse(BaseModel):
    """Schema for task submission response"""

    success: bool = Field(..., description="Whether the task was submitted successfully")
    task_id: str = Field(..., description="Celery task identifier")
    message: str = Field(..., description="Response message")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "task_id": "celery-task-123456789",
                "message": "Task submitted successfully",
                "metadata": {
                    "estimated_duration": "5 minutes",
                    "file_size": 1024000
                }
            }
        }
    )


class TaskStatusResponse(BaseModel):
    """Schema for task status response"""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED)")
    ready: bool = Field(..., description="Whether task is ready")
    successful: Optional[bool] = Field(
        default=None, description="Whether task was successful")
    failed: Optional[bool] = Field(
        default=None, description="Whether task failed")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Task result if available")
    error: Optional[str] = Field(
        default=None, description="Error message if failed")
    meta: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None,
        description="Additional task metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "celery-task-123456789",
                "status": "SUCCESS",
                "ready": True,
                "successful": True,
                "failed": False,
                "result": {
                    "embeddings_count": 100,
                    "processing_time": 45.2
                },
                "error": None,
                "meta": {
                    "progress": 100,
                    "chunks_processed": 100
                }
            }
        }
    )


class TaskResultResponse(BaseModel):
    """Schema for task result response"""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status")
    ready: bool = Field(..., description="Whether task is ready")
    successful: Optional[bool] = Field(
        default=None, description="Whether task was successful")
    failed: Optional[bool] = Field(
        default=None, description="Whether task failed")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Task result")
    error: Optional[str] = Field(
        default=None, description="Error message if failed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "celery-task-123456789",
                "status": "SUCCESS",
                "ready": True,
                "successful": True,
                "failed": False,
                "result": {
                    "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                    "chunks": ["First text chunk", "Second text chunk"],
                    "processing_time": 45.2
                },
                "error": None
            }
        }
    )


class EmbeddingResult(BaseModel):
    """Schema for embedding result data"""

    user_id: str = Field(..., description="User identifier")
    file_id: str = Field(..., description="File identifier")
    provider: str = Field(..., description="AI provider used")
    model_id: str = Field(..., description="Model identifier used")
    total_chunks: int = Field(..., ge=0, description="Total number of chunks processed")
    successful_chunks: int = Field(..., ge=0, description="Number of successfully processed chunks")
    split_config: Dict[str, Any] = Field(..., description="Split configuration used")
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    chunks: List[str] = Field(..., description="Original text chunks")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "file_id": "507f1f77bcf86cd799439012",
                "provider": "huggingface",
                "model_id": "sentence-transformers/all-MiniLM-L6-v2",
                "total_chunks": 100,
                "successful_chunks": 98,
                "split_config": {
                    "chunk_size": 512,
                    "overlap": 50
                },
                "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                "chunks": ["First text chunk", "Second text chunk"],
                "metadata": {
                    "processing_time": 45.2,
                    "model_version": "1.0.0"
                }
            }
        }
    )


class ActiveTasksResponse(BaseModel):
    """Schema for active tasks response"""

    active_tasks: Dict[str, Any] = Field(..., description="Active tasks by worker")
    total_active: int = Field(..., ge=0, description="Total number of active tasks")
    workers: Optional[List[str]] = Field(
        default=None, description="List of worker names")
    message: Optional[str] = Field(
        default=None, description="Additional message")
    error: Optional[str] = Field(
        default=None, description="Error message if any")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "active_tasks": {
                    "worker1": ["task-123", "task-456"],
                    "worker2": ["task-789"]
                },
                "total_active": 3,
                "workers": ["worker1", "worker2"],
                "message": "Active tasks retrieved successfully",
                "error": None
            }
        }
    )


class TaskCancelResponse(BaseModel):
    """Schema for task cancellation response"""

    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Cancellation status")
    message: Optional[str] = Field(
        default=None, description="Cancellation message")
    error: Optional[str] = Field(
        default=None, description="Error message if failed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "celery-task-123456789",
                "status": "REVOKED",
                "message": "Task cancelled successfully",
                "error": None
            }
        }
    )
