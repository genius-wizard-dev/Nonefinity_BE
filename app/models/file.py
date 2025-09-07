from typing import List, Optional, Annotated
from app.schemas.file import ColumnSchema
from beanie import Document, Indexed
from pydantic import  Field
from app.models.time_mixin import TimeMixin
from app.models.soft_delete_mixin import SoftDeleteMixin




class File(Document, TimeMixin, SoftDeleteMixin):
  """File information and schema in MongoDB"""

  # 1. Basic file information
  owner_id: Annotated[str, Indexed(str)] = Field(..., description="User/tenant who owns the file")
  bucket: Annotated[str, Indexed(str)] = Field(..., description="Bucket name in MinIO")
  object_name: Annotated[str, Indexed(str)] = Field(..., description="File path/ID in MinIO")
  file_name: Annotated[str, Indexed(str)] = Field(..., description="Original filename when uploaded")
  file_type: Annotated[str, Indexed(str)] = Field(..., description="File type: csv, xlsx, pdf, json, image...")
  file_size: Optional[Annotated[int, Indexed(int)]] = Field(None, description="File size (bytes)")
  url: Optional[str] = Field(None, description="Public URL to access the file")
  folder_path: Annotated[str, Indexed(str)] = Field(default="/", description="Folder path where file is located")

  # 2. Data schema (if it's a table)
  columns: Optional[List[ColumnSchema]] = Field(None, description="Column schema")

  # 3. Metadata for AI pipeline
  embedding_status: bool = Field(default=False, description="Whether vector embedding is completed")
  qdrant_collection: Optional[str] = Field(None, description="Qdrant collection name")
  tags: Optional[List[str]] = Field(None, description="Tags attached to the dataset")

  # 4. Administration & versioning
  version: int = Field(default=1, description="File/schema version")


  class Settings:
    name = "files"   # collection name in MongoDB
