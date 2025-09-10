from pydantic import BaseModel
from typing import Optional, List


class ColumnSchema(BaseModel):
  """Schema describing a column in the dataset"""
  name: str
  type: str
  nullable: bool
  is_primary: bool
  description: Optional[str]


class FileCreate(BaseModel):
  """Schema for creating a new file (internal use with all fields)"""
  owner_id: str
  bucket: str
  object_name: str
  file_name: str
  file_ext: str
  file_type: str
  file_size: Optional[int] = None
  url: Optional[str] = None
  columns: Optional[List[ColumnSchema]] = None
  tags: Optional[List[str]] = None

class FileUpdate(BaseModel):
  """Schema for updating an existing file"""
  file_name: Optional[str] = None
  file_type: Optional[str] = None
  file_size: Optional[int] = None
  url: Optional[str] = None
  columns: Optional[List[ColumnSchema]] = None
  qdrant_collection: Optional[str] = None
  tags: Optional[List[str]] = None
  version: Optional[int] = None

class FileResponse(BaseModel):
  """Schema for returning file information"""
  id: str
  owner_id: str
  bucket: str
  object_name: str
  file_name: str
  file_ext: str
  file_type: str
  file_size: Optional[int]
  url: Optional[str]
  columns: Optional[List[ColumnSchema]]
  qdrant_collection: Optional[str]
  tags: Optional[List[str]]
  version: int
  created_at: str
  updated_at: str

