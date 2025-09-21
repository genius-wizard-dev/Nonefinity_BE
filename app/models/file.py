from typing import Optional, Annotated
from beanie import Document, Indexed
from pydantic import Field
from app.models.time_mixin import TimeMixin


class File(Document, TimeMixin):
    """File information in MongoDB - stores raw files only"""

    # Basic file information
    owner_id: Annotated[str, Indexed(str)] = Field(..., description="User/tenant who owns the file")
    bucket: Annotated[str, Indexed(str)] = Field(..., description="Bucket name in MinIO")
    file_path: Annotated[str, Indexed(str)] = Field(..., description="File path/ID in MinIO")
    file_name: Annotated[str, Indexed(str)] = Field(..., description="File name without extension")
    file_ext: Annotated[str, Indexed(str)] = Field(..., description="File extension (e.g., .pdf, .jpg)")
    file_type: Annotated[str, Indexed(str)] = Field(..., description="File MIME type: text/csv, image/jpeg, etc.")
    file_size: Optional[Annotated[int, Indexed(int)]] = Field(None, description="File size (bytes)")
    url: Optional[str] = Field(None, description="Public URL to access the file")

    class Settings:
        name = "files"
