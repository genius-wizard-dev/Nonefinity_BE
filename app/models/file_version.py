from typing import Dict, Any, Annotated, Optional
from beanie import Document, Indexed
from pydantic import Field
from app.models.time_mixin import TimeMixin


class FileVersion(Document, TimeMixin):
    """File version information in MongoDB"""

    # Version information
    version: int = Field(..., description="Số thứ tự version")

    # Actions performed on the file
    actions: Optional[Dict[str, Any]] = Field(default=None, description="Các hành động đã thực hiện: edit, delete, add (thêm/xóa cột, dòng, sửa dòng...)")

    # Source path in MinIO/S3
    source: Annotated[str, Indexed(str)] = Field(..., description="Đường dẫn S3/MinIO tới file")

    # Reference to the main file
    raw_id: Annotated[str, Indexed(str)] = Field(..., description="ID của model file chính")

    class Settings:
        name = "file_versions"  # collection name in MongoDB
