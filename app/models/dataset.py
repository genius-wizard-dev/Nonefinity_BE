from typing import List, Optional, Annotated, Dict, Any
from beanie import Document, Indexed
from pydantic import Field
from app.models.time_mixin import TimeMixin


class Dataset(Document, TimeMixin):
    """Dataset information in MongoDB"""

    # Basic dataset information
    name: Annotated[str, Indexed(str)] = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")

    # Owner information
    owner_id: Annotated[str, Indexed(str)] = Field(..., description="User/tenant who owns the dataset")

    # Storage information
    bucket: Annotated[str, Indexed(str)] = Field(..., description="Bucket name in MinIO")
    file_path: Annotated[str, Indexed(str)] = Field(..., description="File path in MinIO (data/{filename}.parquet)")
    # Schema information
    data_schema: List[Dict[str, Any]] = Field(..., description="Dataset schema in JSON format")

    # Statistics
    total_rows: Optional[int] = Field(None, description="Total number of data rows")
    file_size: Optional[int] = Field(None, description="Parquet file size (bytes)")

    # Source file reference
    source_file_id: Optional[str] = Field(None, description="ID of the source file that was converted")

    class Settings:
        name = "datasets"
