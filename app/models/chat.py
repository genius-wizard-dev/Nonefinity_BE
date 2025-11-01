from typing import Annotated, List, Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel
from pydantic import BaseModel
from datetime import datetime

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

    class Settings:
        name = "chat_configs"
        indexes = [
            IndexModel([("owner_id", 1), ("name", 1)]),
            IndexModel([("owner_id", 1), ("created_at", -1)]),
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








