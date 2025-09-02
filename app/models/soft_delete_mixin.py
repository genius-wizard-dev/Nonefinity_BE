from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field


class SoftDeleteMixin(Document):
    is_deleted: bool = Field(
        default=False, description="Soft delete flag"
    )
    deleted_at: Optional[datetime] = Field(
        default=None, description="Deletion timestamp"
    )
