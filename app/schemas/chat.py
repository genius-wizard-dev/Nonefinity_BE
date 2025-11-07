from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ChatConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the chat session")
    chat_model_id: str = Field(..., description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")
    dataset_ids: Optional[List[str]] = Field(None, description="List of dataset IDs")
    instruction_prompt: str = Field("", description="Custom instruction prompt")
    integrations: Optional[dict] = Field(None, description="Third-party integrations configuration (e.g. Google Sheet)")
class ChatConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name of the chat session")
    chat_model_id: Optional[str] = Field(None, description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")
    dataset_ids: Optional[List[str]] = Field(None, description="List of dataset IDs")
    instruction_prompt: Optional[str] = Field(None, description="Custom instruction prompt")
    integrations: Optional[dict] = Field(None, description="Third-party integrations configuration (e.g. Google Sheet)")

class ChatConfigResponse(BaseModel):
    id: str = Field(..., description="Chat config ID")
    name: str = Field(..., min_length=1, max_length=100, description="Name of the chat session")
    chat_model_id: str = Field(..., description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")
    dataset_ids: Optional[List[str]] = Field(None, description="List of dataset IDs")
    instruction_prompt: Optional[str] = Field(None, description="Custom instruction prompt")
    created_at: datetime = Field(..., description="Chat config created at")
    id_alias: str = Field(..., description="ID alias")
    updated_at: Optional[datetime] = Field(None, description="Chat config updated at")
    integrations: Optional[dict] = Field(None, description="Third-party integrations configuration (e.g. Google Sheet)")
    is_used: bool = Field(False, description="Whether this config is being used by at least one session (computed field)")

class ChatConfigListResponse(BaseModel):
    chat_configs: List[ChatConfigResponse] = Field(..., description="List of chat configs")
    total: int = Field(..., ge=0, description="Total number of chat configs")
    skip: int = Field(..., ge=0, description="Number of items skipped")
    limit: int = Field(..., ge=1, description="Number of items per page")


class ChatSessionCreate(BaseModel):
    chat_config_id: str = Field(..., description="Chat config ID")
    name: Optional[str] = Field(None, description="Name of the chat session")


class ToolCall(BaseModel):
    name: str = Field(..., description="Tool name")
    arguments: Optional[Dict[str, Any]] = Field(
        None, description="Arguments passed to the tool"
    )
    result: Optional[Any] = Field(
        None, description="Result returned by the tool (string or structured)"
    )


class ChatMessageResponse(BaseModel):
    id: str = Field(..., description="Chat message ID")
    session_id: str = Field(..., description="Chat session ID")
    role: str = Field(..., description="user / assistant / system / tool")
    content: str = Field("", description="Message content")
    tools: Optional[List[ToolCall]] = Field(None, description="List of tool calls for this message")
    created_at: datetime = Field(..., description="Chat message created at")
    updated_at: Optional[datetime] = Field(None, description="Chat message updated at")

class ChatMessageCreate(BaseModel):
    session_id: str = Field(..., description="Chat session ID")
    role: str = Field(..., description="user / assistant / system / tool")
    content: str = Field("", description="Message content")
    tools: Optional[List[ToolCall]] = Field(None, description="List of tool calls for this message")


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
    role: str = Field(..., description="user / assistant / system / tool")
    content: Optional[str] = Field(None, description="Message content")
    tools: Optional[List[ToolCall]] = Field(None, description="List of tool calls for this message")


class SaveConversationRequest(BaseModel):
    messages: List[SaveChatMessageRequest] = Field(..., description="List of messages to save")
