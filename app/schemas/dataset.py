from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ColumnSchemaBase(BaseModel):
    """Base schema for column definition"""
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Data type (string, integer, float, boolean, date, etc.)")
    desc: Optional[str] = Field(None, description="Column description")


class DatasetBase(BaseModel):
    """Base schema for Dataset"""
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")


class DatasetCreate(DatasetBase):
    """Schema for creating Dataset"""
    owner_id: str = Field(..., description="User/tenant who owns the dataset")
    bucket: str = Field(..., description="Bucket name in MinIO")
    file_path: str = Field(..., description="File path in MinIO (data/{filename}.parquet)")
    data_schema: List[Dict[str, Any]] = Field(..., description="Dataset schema in JSON format")
    total_rows: Optional[int] = Field(None, description="Total number of data rows")
    file_size: Optional[int] = Field(None, description="Parquet file size (bytes)")
    source_file_id: Optional[str] = Field(None, description="ID of the source file that was converted")


class DatasetUpdate(BaseModel):
    """Schema for updating Dataset"""
    name: Optional[str] = Field(None, description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    data_schema: Optional[List[Dict[str, Any]]] = Field(None, description="Dataset schema in JSON format")


class DatasetResponse(DatasetBase):
    """Schema for Dataset response"""
    id: str = Field(..., description="Dataset ID")
    owner_id: str = Field(..., description="User/tenant who owns the dataset")
    bucket: str = Field(..., description="Bucket name in MinIO")
    file_path: str = Field(..., description="File path in MinIO (data/{filename}.parquet)")
    data_schema: List[Dict[str, Any]] = Field(..., description="Dataset schema in JSON format")
    total_rows: Optional[int] = Field(None, description="Total number of data rows")
    file_size: Optional[int] = Field(None, description="Parquet file size (bytes)")
    source_file_id: Optional[str] = Field(None, description="ID of the source file that was converted")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        from_attributes = True


class DatasetStats(BaseModel):
    """Schema for dataset statistics"""
    total_datasets: int = Field(..., description="Total number of datasets")
    total_size: int = Field(..., description="Total size (bytes)")
    total_size_mb: float = Field(..., description="Total size (MB)")
    total_rows: int = Field(..., description="Total number of data rows")


class FileToDatasetRequest(BaseModel):
    """Schema for file to dataset conversion request"""
    file_id: str = Field(..., description="ID of the file to convert")
    dataset_name: str = Field(..., description="Name of the dataset to create")
    description: Optional[str] = Field(None, description="Dataset description")


class DatasetDataResponse(BaseModel):
    """Schema for dataset data response"""
    data: List[Dict[str, Any]] = Field(..., description="Dataset data")
    total_rows: int = Field(..., description="Total number of rows")
    data_schema: List[Dict[str, Any]] = Field(..., description="Dataset schema")
