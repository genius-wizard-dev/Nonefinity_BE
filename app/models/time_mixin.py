from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field


class TimeMixin(Document):
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp")
