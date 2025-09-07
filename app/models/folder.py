from typing import Optional, Annotated
from beanie import Document, Indexed
from pydantic import Field
from app.models.time_mixin import TimeMixin
from app.models.soft_delete_mixin import SoftDeleteMixin

class Folder(Document, TimeMixin, SoftDeleteMixin):
    """Folder structure in MongoDB"""

    owner_id: Annotated[str, Indexed(str)] = Field(..., description="User/tenant who owns the folder")
    folder_name: Annotated[str, Indexed(str)] = Field(..., description="Folder name")
    folder_path: Annotated[str, Indexed(str)] = Field(..., description="Full folder path")
    parent_path: Annotated[str, Indexed(str)] = Field(default="/", description="Parent folder path")

    class Settings:
        name = "folders"
