"""API Key Model"""
from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field
import secrets
import hashlib


class APIKey(Document):
    """API Key for external integrations"""
    
    owner_id: str = Field(..., description="User ID who owns this API key")
    chat_config_id: Optional[str] = Field(default=None, description="Chat config ID this key is scoped to (optional)")
    name: str = Field(..., description="Friendly name for the API key")
    key_prefix: str = Field(..., description="First 8 characters of the key for identification")
    key_hash: str = Field(..., description="Hashed API key")
    is_active: bool = Field(default=True, description="Whether the key is active")
    last_used_at: Optional[datetime] = Field(default=None, description="Last time the key was used")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration date")
    permissions: list[str] = Field(default_factory=list, description="List of permissions")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "api_keys"
        indexes = [
            "owner_id",
            "key_hash",
            "chat_config_id",
            [("owner_id", 1), ("is_active", 1)],
            [("owner_id", 1), ("chat_config_id", 1)],
        ]

    @staticmethod
    def generate_key() -> str:
        """Generate a new API key"""
        # Format: nf_live_<random_string>
        random_part = secrets.token_urlsafe(32)
        return f"nf_live_{random_part}"

    @staticmethod
    def hash_key(api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """Get the prefix of an API key for display"""
        return api_key[:8] if len(api_key) >= 8 else api_key

    def is_expired(self) -> bool:
        """Check if the API key is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid for use"""
        return self.is_active and not self.is_expired()

    async def mark_used(self):
        """Update last_used_at timestamp"""
        self.last_used_at = datetime.utcnow()
        await self.save()
