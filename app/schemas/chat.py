from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, validator

class ChatConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the chat session")
    chat_model_id: str = Field(..., description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")
    dataset_ids: Optional[List[str]] = Field(None, description="List of dataset IDs")
    instruction_prompt: str = Field("", description="Custom instruction prompt")

class ChatConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name of the chat session")
    chat_model_id: Optional[str] = Field(None, description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")
    instruction_prompt: Optional[str] = Field(None, description="Custom instruction prompt")

class ChatConfigResponse(BaseModel):
    id: str = Field(..., description="Chat config ID")
    name: str = Field(..., min_length=1, max_length=100, description="Name of the chat session")
    chat_model_id: str = Field(..., description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")
    dataset_ids: Optional[List[str]] = Field(None, description="List of dataset IDs")
    instruction_prompt: Optional[str] = Field(None, description="Custom instruction prompt")
    created_at: datetime = Field(..., description="Chat config created at")
    updated_at: Optional[datetime] = Field(None, description="Chat config updated at")

class ChatConfigListResponse(BaseModel):
    chat_configs: List[ChatConfigResponse] = Field(..., description="List of chat configs")
    total: int = Field(..., ge=0, description="Total number of chat configs")
    skip: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Number of items per page")


class ChatSessionCreate(BaseModel):
    chat_config_id: str = Field(..., description="Chat config ID")
    name: Optional[str] = Field(None, description="Name of the chat session")


class ChatMessageResponse(BaseModel):
    id: str = Field(..., description="Chat message ID")
    session_id: str = Field(..., description="Chat session ID")
    role: str = Field(..., description="user / assistant / system / tool")
    content: str = Field("", description="Message content")
    tool_calls: Optional[List[dict]] = Field(None, description="Tool calls made by the model")
    tool_results: Optional[List[dict]] = Field(None, description="Tool results made by the model")
    created_at: datetime = Field(..., description="Chat message created at")
    updated_at: Optional[datetime] = Field(None, description="Chat message updated at")

class ChatMessageCreate(BaseModel):
    session_id: str = Field(..., description="Chat session ID")
    role: str = Field(..., description="user / assistant / system / tool")
    content: str = Field("", description="Message content")
    tool_calls: Optional[List[dict]] = Field(None, description="Tool calls made by the model")
    tool_results: Optional[List[dict]] = Field(None, description="Tool results made by the model")


class ChatMessageListResponse(BaseModel):
    chat_messages: List[ChatMessageResponse] = Field(..., description="List of chat messages")
    total: int = Field(..., ge=0, description="Total number of chat messages")
    skip: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Number of items per page")


class ChatSessionResponse(BaseModel):
    id: str = Field(..., description="Chat session ID")
    chat_config_id: str = Field(..., description="Chat config ID")
    name: Optional[str] = Field(None, description="Name of the chat session")
    created_at: datetime = Field(..., description="Chat session created at")
    updated_at: Optional[datetime] = Field(None, description="Chat session updated at")
    messages: Optional[ChatMessageListResponse] = Field(None, description="List of chat messages")

class ChatSessionListResponse(BaseModel):
    chat_sessions: List[ChatSessionResponse] = Field(..., description="List of chat sessions")
    total: int = Field(..., ge=0, description="Total number of chat sessions")
    skip: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Number of items per page")




class StreamChatMessageRequest(BaseModel):
    message: str = Field("", description="Message content")


class SaveChatMessageRequest(BaseModel):
    session_id: str = Field(..., description="ChatSession ID")
    owner_id: str = Field(..., description="Owner ID from authentication")
    role: str = Field(..., description="user / assistant / system / tool")
    question: Optional[str] = Field(None, description="Message content")
    answer: Optional[str] = Field(None, description="Message content")
    tool_calls: Optional[List[dict]] = Field(None, description="Tool calls made by the model")
    tool_results: Optional[List[dict]] = Field(None, description="Tool results made by the model")
