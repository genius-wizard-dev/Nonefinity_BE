from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TimeMixin(BaseModel):
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp")
