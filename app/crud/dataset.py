from typing import List, Optional, Dict, Any
from app.crud.base import BaseCRUD
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate, DatasetUpdate
from app.utils import get_logger

logger = get_logger(__name__)


class DatasetCRUD(BaseCRUD[Dataset, DatasetCreate, DatasetUpdate]):
    """CRUD operations for Dataset"""

    def __init__(self):
        super().__init__(Dataset)

    async def get_by_owner_id(self, owner_id: str) -> List[Dataset]:
        """Get all datasets of a user"""
        try:
            filter_dict = {"owner_id": owner_id}
            return await self.list(filter_=filter_dict)
        except Exception as e:
            logger.error(f"Failed to get datasets by owner_id {owner_id}: {str(e)}")
            return []

    async def get_by_name_and_owner(self, name: str, owner_id: str) -> Optional[Dataset]:
        """Find dataset by name and owner"""
        try:
            filter_dict = {"name": name, "owner_id": owner_id}
            datasets = await self.list(filter_=filter_dict)
            return datasets[0] if datasets else None
        except Exception as e:
            logger.error(f"Failed to get dataset by name {name} and owner {owner_id}: {str(e)}")
            return None

    async def search_by_name(self, owner_id: str, search_term: str, limit: int = 50) -> List[Dataset]:
        """Search datasets by name"""
        try:
            # Use regex for search
            from beanie.operators import RegEx
            query = {
                "owner_id": owner_id,
                "name": RegEx(pattern=search_term, options="i")  # case insensitive
            }
            return await Dataset.find(query).limit(limit).to_list()
        except Exception as e:
            logger.error(f"Failed to search datasets: {str(e)}")
            return []

    async def get_datasets_by_source_file(self, source_file_id: str) -> List[Dataset]:
        """Get datasets created from a source file"""
        try:
            filter_dict = {"source_file_id": source_file_id}
            return await self.list(filter_=filter_dict)
        except Exception as e:
            logger.error(f"Failed to get datasets by source file {source_file_id}: {str(e)}")
            return []

    async def get_stats_by_owner(self, owner_id: str) -> Dict[str, Any]:
        """Get dataset statistics for user"""
        try:
            datasets = await self.get_by_owner_id(owner_id)
            total_datasets = len(datasets)
            total_size = sum(d.file_size or 0 for d in datasets)
            total_rows = sum(d.total_rows or 0 for d in datasets)

            return {
                "total_datasets": total_datasets,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
                "total_rows": total_rows
            }
        except Exception as e:
            logger.error(f"Failed to get dataset stats for owner {owner_id}: {str(e)}")
            return {
                "total_datasets": 0,
                "total_size": 0,
                "total_size_mb": 0,
                "total_rows": 0
            }


# Create instance
dataset_crud = DatasetCRUD()
