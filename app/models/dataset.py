from typing import List, Dict, Any, Annotated, Optional
from beanie import Document, Indexed
from pydantic import Field
from app.models.time_mixin import TimeMixin


class Dataset(Document, TimeMixin):
    """Dataset model for managing DuckLake tables"""

    name: Annotated[str, Indexed(str)] = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    owner_id: Annotated[str, Indexed(str)] = Field(..., description="User ID who owns the dataset")
    data_schema: List[Dict[str, Any]] = Field(..., description="Schema của table")

    class Settings:
        name = "datasets"

    def __repr__(self):
        return f"<Dataset(id='{self.id}', name='{self.name}', owner_id='{self.owner_id}')>"
