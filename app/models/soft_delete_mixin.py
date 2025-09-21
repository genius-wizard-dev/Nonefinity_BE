from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SoftDeleteMixin(BaseModel):
    is_deleted: bool = Field(
        default=False, description="Soft delete flag"
    )
    deleted_at: Optional[datetime] = Field(
        default=None, description="Deletion timestamp"
    )
