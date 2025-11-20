from __future__ import annotations

from typing import Optional, Dict, Any, Literal

from beanie import Document
from pydantic import Field

from app.models.time_mixin import TimeMixin


class Task(TimeMixin, Document):
    task_id: str = Field(..., description="Celery task identifier")
    task_type: Literal["embedding", "search", "text_embedding"] = Field(..., description="Type of task")
    user_id: str = Field(..., description="Owner user id")
    file_id: Optional[str] = Field(default=None, description="Related file id if any")
    knowledge_store_id: Optional[str] = Field(default=None, description="Knowledge store id if any")
    provider: Optional[str] = Field(default=None, description="Provider used")
    model_id: Optional[str] = Field(default=None, description="Model identifier used")

    status: Literal[
        "PENDING",
        "STARTED",
        "PROGRESS",
        "SUCCESS",
        "FAILURE",
        "RETRY",
        "REVOKED",
        "CANCELLED",
        "ERROR",
    ] = Field(default="PENDING", description="Current task status")

    metadata: Optional[Dict[str, Any]] = Field(default=None)
    error: Optional[str] = Field(default=None)

    class Settings:
        name = "tasks"
        indexes = ["task_id", "user_id", "task_type"]


