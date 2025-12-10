from typing import Annotated, Any, Dict, List, Optional
from beanie import Document, Indexed
from pydantic import Field, field_validator
from pymongo import IndexModel

from app.models.time_mixin import TimeMixin


class ChatConfig(TimeMixin, Document):
    """Chat configuration model"""
    name: Annotated[str, Indexed()] = Field(..., min_length=1, max_length=100, description="Name of the chat session")
    owner_id: Annotated[str, Indexed()] = Field(..., description="Owner ID from authentication")

    # Model configurations
    chat_model_id: str = Field(..., description="AI model ID used for the chat")

    # Knowledge base configurations
    dataset_ids: List[str] = Field(default_factory=list, description="List of dataset IDs")

    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")

    # Custom instructions
    instruction_prompt: str = Field("", description="Custom instruction prompt")

    id_alias: Optional[Annotated[str, Indexed()]] = Field(None, description="ID alias")

    mcp_ids: List[str] = Field(default_factory=list, description="List of MCP configuration MongoDB IDs")
    selected_tools: Dict[str, Any] = Field(default_factory=dict, description="Selected tools per integration: {integration_name: {tools: [tool_slug, ...]}}")
    middleware: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of middleware configurations, e.g. [{'summary': {'model_id': '...', ...}}]")

    @field_validator('middleware', mode='before')
    @classmethod
    def convert_none_to_empty_list(cls, v):
        """Convert None to empty list for middleware"""
        if v is None:
            return []
        return v

    class Settings:
        name = "chat_configs"
        indexes = [
            IndexModel([("owner_id", 1), ("name", 1)]),
            IndexModel([("owner_id", 1), ("created_at", -1)]),
            IndexModel([("owner_id", 1), ("id_alias", 1)]),
        ]


class ChatSession(TimeMixin, Document):
    """Phiên chat (dùng luôn làm thread)"""
    chat_config_id: Annotated[str, Indexed()] = Field(..., description="ChatConfig ID")
    owner_id: Annotated[str, Indexed()] = Field(..., description="Owner ID from authentication")
    name: Optional[str] = Field(None, description="Name of the chat session")

    class Settings:
        name = "chat_sessions"
        indexes = [
            IndexModel([("owner_id", 1), ("created_at", -1)]),
            IndexModel([("owner_id", 1), ("name", 1)]),
        ]


class ChatMessage(TimeMixin, Document):
    """Tin nhắn thuộc một session"""
    session_id: Annotated[str, Indexed()] = Field(..., description="ChatSession ID")
    owner_id: Annotated[str, Indexed()] = Field(..., description="Owner ID from authentication")
    role: str = Field(..., description="user / assistant / system / tool")
    content: str = Field("", description="Message content")
    tools: Optional[List[dict]] = Field(None, description="Tools data as sent by frontend")


    class Settings:
        name = "chat_messages"
        indexes = [
            IndexModel([("session_id", 1), ("created_at", -1)]),
            IndexModel([("owner_id", 1), ("created_at", -1)]),
        ]








