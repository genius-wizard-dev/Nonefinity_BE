from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, ConfigDict
from datetime import datetime


class DataSchemaField(BaseModel):
    """Schema field for dataset table"""
    column_name: str = Field(..., description="Column name")
    column_type: str = Field(..., description="Data type (string, integer, float, boolean, etc.)")
    desc: Optional[str] = Field(None, description="Column description")
    old_name: Optional[str] = Field(None, description="Old column name for renaming")

    @validator('column_type')
    def validate_type(cls, v):
        valid_types = [
            'string', 'varchar', 'text',
            'integer', 'bigint', 'smallint', 'tinyint',
            'float', 'double', 'decimal', 'numeric',
            'boolean', 'bool',
            'date', 'timestamp', 'datetime',
            'json', 'array', 'struct'
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid data type. Must be one of: {', '.join(valid_types)}")
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "column_name": "customer_id",
                "column_type": "integer",
                "desc": "Unique customer identifier",
                "old_name": None
            }
        }
    )


class DatasetBase(BaseModel):
    """Base schema for Dataset"""
    name: str = Field(..., min_length=1, max_length=255, description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    data_schema: List[DataSchemaField] = Field(..., min_items=1, description="Table schema")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Dataset name cannot be empty")
        return v.strip()


class DatasetCreate(DatasetBase):
    """Schema for creating dataset"""
    pass


class DatasetUpdate(BaseModel):
    """Schema for updating dataset (name and description only)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Dataset name cannot be empty")
        return v.strip() if v else v




class DatasetDescriptionsUpdate(BaseModel):
    """Schema for updating dataset column descriptions"""
    descriptions: dict = Field(..., description="Dictionary mapping column names to descriptions")


class DatasetUpdateRequest(BaseModel):
    """Schema for updating dataset name and description via JSON"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Dataset name cannot be empty")
        return v.strip() if v else v




class Dataset(DatasetBase):
    """Schema for Dataset response"""
    id: str = Field(..., description="Unique dataset identifier")
    owner_id: str = Field(..., description="Owner user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_used: bool = Field(False, description="Whether the dataset is used in any chat config")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Customer Data",
                "description": "Customer information dataset",
                "data_schema": [
                    {
                        "column_name": "customer_id",
                        "column_type": "integer",
                        "desc": "Unique customer identifier"
                    },
                    {
                        "column_name": "name",
                        "column_type": "string",
                        "desc": "Customer full name"
                    }
                ],
                "owner_id": "507f1f77bcf86cd799439012",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class DatasetList(BaseModel):
    """Schema for dataset list response"""
    datasets: List[Dataset] = Field(..., description="List of datasets")
    total: int = Field(..., ge=0, description="Total number of datasets")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Number of items per page")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "datasets": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "name": "Customer Data",
                        "description": "Customer information dataset",
                        "data_schema": [],
                        "owner_id": "507f1f77bcf86cd799439012",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 100
            }
        }
    )


class DatasetData(BaseModel):
    """Schema for dataset data response"""
    data: List[Dict[str, Any]] = Field(..., description="Dataset rows")
    total_rows: Optional[int] = Field(None, description="Total number of rows in dataset")
    offset: int = Field(..., ge=0, description="Number of rows skipped")
    limit: int = Field(..., ge=1, description="Number of rows returned")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [
                    {
                        "customer_id": 1,
                        "name": "John Doe",
                        "email": "john@example.com"
                    },
                    {
                        "customer_id": 2,
                        "name": "Jane Smith",
                        "email": "jane@example.com"
                    }
                ],
                "total_rows": 1000,
                "offset": 0,
                "limit": 100
            }
        }
    )


class DatasetCreateRequest(BaseModel):
    """Schema for creating dataset via JSON"""
    dataset_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    data_schema: List[DataSchemaField] = Field(..., min_items=1, description="Table schema")

    @validator('dataset_name')
    def validate_dataset_name(cls, v):
        if not v.strip():
            raise ValueError("Dataset name cannot be empty")
        return v.strip()

class DatasetConvertRequest(BaseModel):
    """Schema for converting file to dataset"""
    file_id: str = Field(..., description="File ID to convert")
    dataset_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None)

    @validator('dataset_name')
    def validate_dataset_name(cls, v):
        if not v.strip():
            raise ValueError("Dataset name cannot be empty")
        return v.strip()

class DatasetQueryRequest(BaseModel):
    """Schema for querying dataset"""
    query: str = Field(..., min_length=1, description="SQL query")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")

class DatasetSchemaUpdateRequest(BaseModel):
    """Schema for updating dataset schema descriptions"""
    descriptions: Dict[str, str] = Field(..., min_items=1, description="Column descriptions mapping")

class FileUploadRequest(BaseModel):
    """Schema for file upload request"""
    dataset_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None)

    @validator('dataset_name')
    def validate_dataset_name(cls, v):
        if not v.strip():
            raise ValueError("Dataset name cannot be empty")
        return v.strip()
