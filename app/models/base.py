from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field


class BaseDocument(Document):
    """Base document with common fields"""
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    class Settings:
        # Use the collection name based on the class name in snake_case
        use_state_management = True
        
    async def save(self, *args, **kwargs):
        """Override save to update the updated_at field"""
        self.updated_at = datetime.utcnow()
        return await super().save(*args, **kwargs)
    
    def model_dump_json(self, **kwargs):
        """Custom JSON serialization"""
        return super().model_dump_json(by_alias=True, exclude_none=True, **kwargs)
