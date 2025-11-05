from typing import List, Optional
from app.crud.base import BaseCRUD
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate, DatasetUpdate
from app.utils import get_logger
from bson import ObjectId
logger = get_logger(__name__)


class DatasetCRUD(BaseCRUD[Dataset, DatasetCreate, DatasetUpdate]):
    def __init__(self):
        super().__init__(Dataset)

    async def get_by_name(self, name: str, owner_id: str) -> Optional[Dataset]:
        """Get dataset by name"""
        # Get dataset by name and owner_id, only return if not deleted
        return await self.get_one(
            filter_={"name": name, "owner_id": owner_id},
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

    async def update_schema(self, dataset_id: str, new_schema: List) -> Dataset:
        """Update dataset schema"""
        dataset = await self.get_by_id(dataset_id, include_deleted=False)
        if not dataset:
            raise ValueError(f"Dataset with id {dataset_id} not found")

        # Convert DataSchemaField objects to dict if needed
        schema_data = []
        for field in new_schema:
            if hasattr(field, 'dict'):
                schema_data.append(field.dict())
            else:
                schema_data.append(field)

        update_data = {"data_schema": schema_data}
        updated_dataset = await self.update(dataset, update_data)

        logger.info(f"Updated schema for dataset: {dataset_id}")
        return updated_dataset

    async def get_by_owner_and_ids(self, owner_id: str, dataset_ids: List[str]) -> List[Dataset]:
        """Get datasets by owner and IDs"""
        return await self.list(
            filter_={"owner_id": owner_id, "_id": {"$in": [ObjectId(dataset_id) for dataset_id in dataset_ids]}},
            include_deleted=False
        )


dataset_crud = DatasetCRUD()
