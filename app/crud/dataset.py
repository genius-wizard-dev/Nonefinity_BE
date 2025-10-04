from typing import List, Optional
from app.crud.base import BaseCRUD
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate, DatasetUpdate
from app.utils import get_logger

logger = get_logger(__name__)


class DatasetCRUD(BaseCRUD[Dataset, DatasetCreate, DatasetUpdate]):
    def __init__(self):
        super().__init__(Dataset)

    async def get_by_name(self, name: str) -> Optional[Dataset]:
        """Get dataset by name"""
        return await self.get_one(
            filter_={"name": name},
            include_deleted=False
        )


    async def create_with_owner(self, owner_id: str, obj_in: DatasetCreate) -> Dataset:
        """Create dataset with owner"""
        # Create dataset with owner_id and name
        data = obj_in.model_dump()
        data["owner_id"] = owner_id
        data["data_schema"] = [field.dict() for field in obj_in.data_schema]

        db_obj = Dataset(**data)
        await db_obj.insert()

        logger.info(f"Created dataset: {db_obj.id} for owner: {owner_id}")
        return db_obj

    async def get_by_owner(self, owner_id: str, skip: int = 0, limit: int = 100) -> List[Dataset]:
        """Get datasets by owner"""
        return await self.list(
            filter_={"owner_id": owner_id},
            skip=skip,
            limit=limit,
            include_deleted=False
        )

    async def get_by_owner_and_id(self, owner_id: str, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by owner and ID"""
        dataset = await self.get_by_id(dataset_id, include_deleted=False)
        if dataset and dataset.owner_id == owner_id:
            return dataset
        return None


    async def count_by_owner(self, owner_id: str) -> int:
        """Count datasets by owner"""
        datasets = await self.list(
            filter_={"owner_id": owner_id},
            include_deleted=False
        )
        return len(datasets)

    async def update_schema(self, db_obj: Dataset, new_schema: List[dict]) -> Dataset:
        """Update dataset schema"""
        update_data = {"data_schema": new_schema}
        updated_dataset = await self.update(db_obj, update_data)

        logger.info(f"Updated schema for dataset: {db_obj.id}")
        return updated_dataset




# Create instance
dataset_crud = DatasetCRUD()
