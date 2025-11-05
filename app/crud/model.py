from typing import List, Optional, Dict
from bson import ObjectId

from app.crud.base import BaseCRUD
from app.models.model import Model, ModelType
from app.schemas.model import ModelCreate, ModelUpdate


class ModelCRUD(BaseCRUD[Model, ModelCreate, ModelUpdate]):
    def __init__(self):
        super().__init__(Model)

    async def get_by_owner(
        self,
        owner_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Model]:
        """Get all models for a specific owner"""
        query = {
            "owner_id": owner_id,
            "name": {"$ne": None},
            "is_active": {"$ne": None}
        }

        cursor = self.model.find(query).skip(skip).limit(limit)
        return await cursor.to_list()

    async def get_models_with_filters(
        self,
        owner_id: str,
        skip: int = 0,
        limit: int = 50,
        model_type: Optional[ModelType] = None,
        credential_id: Optional[str] = None,
        active_only: bool = False
    ) -> List[Model]:
        """Get models with various filtering conditions"""
        # Build MongoDB query with all conditions
        query = {"owner_id": owner_id}

        # Add type filter if specified
        if model_type is not None:
            query["type"] = model_type

        # Add credential filter if specified
        if credential_id is not None:
            query["credential_id"] = credential_id

        # Add active filter if specified
        if active_only:
            query["is_active"] = True
        else:
            # Only add None filter if not already filtering by is_active
            query["is_active"] = {"$ne": None}

        # Add filters to exclude documents with None values for required fields
        query["name"] = {"$ne": None}

        cursor = self.model.find(query).skip(skip).limit(limit)
        return await cursor.to_list()

    async def count_models_with_filters(
        self,
        owner_id: str,
        model_type: Optional[ModelType] = None,
        credential_id: Optional[str] = None,
        active_only: bool = False
    ) -> int:
        """Count models with various filtering conditions"""
        # Build MongoDB query with all conditions
        query = {"owner_id": owner_id}

        # Add type filter if specified
        if model_type is not None:
            query["type"] = model_type

        # Add credential filter if specified
        if credential_id is not None:
            query["credential_id"] = credential_id

        # Add active filter if specified
        if active_only:
            query["is_active"] = True
        else:
            # Only add None filter if not already filtering by is_active
            query["is_active"] = {"$ne": None}

        # Add filters to exclude documents with None values for required fields
        query["name"] = {"$ne": None}

        return await self.model.find(query).count()

    async def get_by_owner_and_id(
        self,
        owner_id: str,
        model_id: str,
    ) -> Optional[Model]:
        """Get a specific model by owner and ID"""
        query = {"_id": ObjectId(model_id), "owner_id": owner_id}

        return await self.model.find_one(query)

    async def get_by_credential(
        self,
        owner_id: str,
        credential_id: str,
    ) -> List[Model]:
        """Get all models for a specific credential"""
        query = {"owner_id": owner_id, "credential_id": credential_id}

        return await self.model.find(query).to_list()

    async def get_by_type(
        self,
        owner_id: str,
        model_type: ModelType,
    ) -> List[Model]:
        """Get all models of a specific type for an owner"""
        query = {"owner_id": owner_id, "type": model_type}

        return await self.model.find(query).to_list()


    async def check_name_exists(
        self,
        owner_id: str,
        name: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """Check if a model name already exists for an owner"""
        query = {"owner_id": owner_id, "name": name}
        if exclude_id:
            query["_id"] = {"$ne": ObjectId(exclude_id)}

        existing = await self.model.find_one(query)
        return existing is not None



    async def create_with_owner(self, owner_id: str, obj_in: ModelCreate) -> Model:
        """Create model with owner"""
        data = obj_in.model_dump()
        data["owner_id"] = owner_id


        db_obj = self.model(**data)
        await db_obj.insert()
        return db_obj

    async def get_active_models(
        self,
        owner_id: str,
    ) -> List[Model]:
        """Get all active models for an owner"""
        query = {"owner_id": owner_id, "is_active": True}

        return await self.model.find(query).to_list()

    async def count_by_owner(
        self,
        owner_id: str,
    ) -> int:
        """Count total models for an owner"""
        query = {"owner_id": owner_id}

        return await self.model.find(query).count()

    async def get_stats(
        self,
        owner_id: str,
    ) -> Dict[str, int]:
        """Get model statistics for an owner"""
        base_query = {"owner_id": owner_id}

        # Count all models
        total_models = await self.model.find(base_query).count()

        # Count by type
        chat_models = await self.model.find({**base_query, "type": ModelType.CHAT}).count()
        embedding_models = await self.model.find({**base_query, "type": ModelType.EMBEDDING}).count()

        # Count by status
        active_models = await self.model.find({**base_query, "is_active": True}).count()
        inactive_models = await self.model.find({**base_query, "is_active": False}).count()

        return {
            "total_models": total_models,
            "chat_models": chat_models,
            "embedding_models": embedding_models,
            "active_models": active_models,
            "inactive_models": inactive_models
        }

    async def count_credential_usage(self, credential_id: str) -> int:
        credential_id = str(credential_id)
        """Count usage by credential ID"""
        return await self.model.find({"credential_id": credential_id}).count()



model_crud = ModelCRUD()
