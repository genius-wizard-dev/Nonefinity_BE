from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, validator


class ChatBase(BaseModel):
    """Base schema for chat"""
    name: str = Field(..., min_length=1, max_length=100, description="Name of the chat session")
    chat_model_id: str = Field(..., description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: int = Field(2048, ge=1, description="Maximum tokens for response")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    dataset_ids: List[str] = Field(default_factory=list, description="List of dataset IDs")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")
    instruction_prompt: str = Field("", description="Custom instruction prompt")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Chat name cannot be empty")
        return v.strip()


class ChatCreate(ChatBase):
    """Schema for creating a new chat"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "My AI Assistant Chat",
                "chat_model_id": "65f1234567890abcdef12345",
                "embedding_model_id": "65f1234567890abcdef12346",
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 1.0,
                "dataset_ids": ["65f1234567890abcdef12347"],
                "knowledge_store_id": "65f1234567890abcdef12348",
                "instruction_prompt": "You are a helpful AI assistant."
            }
        }
    )


class ChatUpdate(BaseModel):
    """Schema for updating chat"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name of the chat session")
    chat_model_id: Optional[str] = Field(None, description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens for response")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    dataset_ids: Optional[List[str]] = Field(None, description="List of dataset IDs")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID")
    instruction_prompt: Optional[str] = Field(None, description="Custom instruction prompt")

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Chat name cannot be empty")
        return v.strip() if v else v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Chat Name",
                "temperature": 0.8,
                "max_tokens": 4096,
                "instruction_prompt": "You are an expert AI assistant."
            }
        }
    )


class ChatResponse(BaseModel):
    """Schema for chat response"""
    id: str = Field(..., description="Chat ID")
    name: str = Field(..., description="Name of the chat session")
    owner_id: str = Field(..., description="Owner ID")
    chat_model_id: str = Field(..., description="AI model ID")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID")
    temperature: float = Field(..., description="Sampling temperature")
    max_tokens: int = Field(..., description="Maximum tokens")
    top_p: float = Field(..., description="Nucleus sampling parameter")
    dataset_ids: List[str] = Field(default_factory=list, description="Dataset IDs")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID")
    instruction_prompt: str = Field("", description="Instruction prompt")
    message_count: int = Field(0, description="Number of messages")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "65f1234567890abcdef12345",
                "name": "My AI Assistant Chat",
                "owner_id": "user_2abc123def456",
                "chat_model_id": "65f1234567890abcdef12345",
                "embedding_model_id": "65f1234567890abcdef12346",
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 1.0,
                "dataset_ids": ["65f1234567890abcdef12347"],
                "knowledge_store_id": "65f1234567890abcdef12348",
                "instruction_prompt": "You are a helpful AI assistant.",
                "message_count": 5,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class ChatListResponse(BaseModel):
    """Schema for chat list response"""
    id: str = Field(..., description="Chat ID")
    name: str = Field(..., description="Chat name")
    owner_id: str = Field(..., description="Owner ID")
    chat_model_id: str = Field(..., description="Chat model ID")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID")
    dataset_ids: List[str] = Field(default_factory=list, description="Dataset IDs")
    message_count: int = Field(0, description="Number of messages")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "65f1234567890abcdef12345",
                "name": "My AI Assistant Chat",
                "owner_id": "user_2abc123def456",
                "chat_model_id": "65f1234567890abcdef12346",
                "embedding_model_id": "65f1234567890abcdef12347",
                "knowledge_store_id": "65f1234567890abcdef12348",
                "dataset_ids": ["65f1234567890abcdef12349"],
                "message_count": 5,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


# Chat History / Message schemas
class ChatMessageBase(BaseModel):
    """Base schema for chat message"""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class ChatMessageCreate(ChatMessageBase):
    """Schema for creating a new chat message"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "user",
                "content": "Hello, how can you help me?"
            }
        }
    )


class ChatMessageResponse(BaseModel):
    """Schema for chat message response"""
    id: str = Field(..., description="Message ID")
    chat_id: str = Field(..., description="Chat ID")
    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    message_order: int = Field(..., description="Message order")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "65f1234567890abcdef12345",
                "chat_id": "65f1234567890abcdef12346",
                "role": "user",
                "content": "Hello, how can you help me?",
                "message_order": 1,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    )


# Request schemas for API endpoints
class ChatCreateRequest(BaseModel):
    """Request schema for creating chat"""
    name: str = Field(..., min_length=1, max_length=100, description="Chat name")
    chat_model_id: str = Field(..., description="AI model ID")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional)")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: int = Field(2048, ge=1, description="Maximum tokens")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling")
    dataset_ids: List[str] = Field(default_factory=list, description="Dataset IDs")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")
    instruction_prompt: str = Field("", description="Instruction prompt")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Chat name cannot be empty")
        return v.strip()


class ChatUpdateRequest(BaseModel):
    """Request schema for updating chat"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Chat name")
    chat_model_id: Optional[str] = Field(None, description="AI model ID")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, ge=1, description="Maximum tokens")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling")
    dataset_ids: Optional[List[str]] = Field(None, description="Dataset IDs")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID")
    instruction_prompt: Optional[str] = Field(None, description="Instruction prompt")

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Chat name cannot be empty")
        return v.strip() if v else v
