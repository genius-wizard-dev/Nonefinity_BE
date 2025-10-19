from typing import Annotated, List, Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel

from app.models.time_mixin import TimeMixin


class Chat(TimeMixin, Document):
    """Chat configuration model"""
    name: Annotated[str, Indexed()] = Field(..., min_length=1, max_length=100, description="Name of the chat session")
    owner_id: Annotated[str, Indexed()] = Field(..., description="Owner ID from authentication")

    # Model configurations
    chat_model_id: str = Field(..., description="AI model ID used for the chat")
    embedding_model_id: Optional[str] = Field(None, description="Embedding model ID (optional for AI-only chat)")

    # Generation parameters
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: int = Field(2048, ge=1, description="Maximum tokens for response")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")

    # Knowledge base configurations
    dataset_ids: List[str] = Field(default_factory=list, description="List of dataset IDs")
    knowledge_store_id: Optional[str] = Field(None, description="Knowledge store ID (optional)")

    # Custom instructions
    instruction_prompt: str = Field("", description="Custom instruction prompt")

    # Statistics
    message_count: int = Field(0, description="Number of messages in chat history")

    class Settings:
        name = "chats"
        indexes = [
            IndexModel([("owner_id", 1), ("name", 1)]),
            IndexModel([("owner_id", 1), ("created_at", -1)]),
        ]


class ChatHistory(TimeMixin, Document):
    """Chat history model - separate collection for message storage"""
    chat_id: Annotated[str, Indexed()] = Field(..., description="Chat ID this message belongs to")
    owner_id: Annotated[str, Indexed()] = Field(..., description="Owner ID from authentication")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    message_order: int = Field(..., description="Order of message in chat")

    class Settings:
        name = "chat_histories"
        indexes = [
            IndexModel([("chat_id", 1), ("message_order", 1)]),
            IndexModel([("owner_id", 1), ("created_at", -1)]),
            IndexModel([("chat_id", 1), ("created_at", 1)]),
        ]




