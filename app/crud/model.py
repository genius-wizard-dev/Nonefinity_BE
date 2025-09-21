from typing import List, Optional, Dict, Any
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
        include_deleted: bool = False
    ) -> List[Model]:
        """Get all models for a specific owner"""
        query = {"owner_id": owner_id}
        if not include_deleted:
            query["is_deleted"] = False

        cursor = self.model.find(query).skip(skip).limit(limit)
        return await cursor.to_list()

    async def get_by_owner_and_id(
        self,
        owner_id: str,
        model_id: str,
        include_deleted: bool = False
    ) -> Optional[Model]:
        """Get a specific model by owner and ID"""
        query = {"_id": ObjectId(model_id), "owner_id": owner_id}
        if not include_deleted:
            query["is_deleted"] = False

        return await self.model.find_one(query)

    async def get_by_credential(
        self,
        owner_id: str,
        credential_id: str,
        include_deleted: bool = False
    ) -> List[Model]:
        """Get all models for a specific credential"""
        query = {"owner_id": owner_id, "credential_id": credential_id}
        if not include_deleted:
            query["is_deleted"] = False

        return await self.model.find(query).to_list()

    async def get_by_type(
        self,
        owner_id: str,
        model_type: ModelType,
        include_deleted: bool = False
    ) -> List[Model]:
        """Get all models of a specific type for an owner"""
        query = {"owner_id": owner_id, "type": model_type}
        if not include_deleted:
            query["is_deleted"] = False

        return await self.model.find(query).to_list()

    async def get_default_model(
        self,
        owner_id: str,
        model_type: ModelType,
        include_deleted: bool = False
    ) -> Optional[Model]:
        """Get the default model for a specific type and owner"""
        query = {
            "owner_id": owner_id,
            "type": model_type,
            "is_default": True,
            "is_active": True
        }
        if not include_deleted:
            query["is_deleted"] = False

        return await self.model.find_one(query)

    async def check_name_exists(
        self,
        owner_id: str,
        name: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """Check if a model name already exists for an owner"""
        query = {"owner_id": owner_id, "name": name, "is_deleted": False}
        if exclude_id:
            query["_id"] = {"$ne": ObjectId(exclude_id)}

        existing = await self.model.find_one(query)
        return existing is not None

    async def set_default_model(
        self,
        owner_id: str,
        model_id: str,
        model_type: ModelType
    ) -> bool:
        """Set a model as default, unsetting others of the same type"""
        try:
            # First, unset all other default models of the same type
            await self.model.find(
                {
                    "owner_id": owner_id,
                    "type": model_type,
                    "is_deleted": False,
                    "_id": {"$ne": ObjectId(model_id)}
                }
            ).update_many({"$set": {"is_default": False}})

            # Then set the specified model as default
            result = await self.model.find_one(
                {"_id": ObjectId(model_id), "owner_id": owner_id, "is_deleted": False}
            )

            if result:
                await result.set({"is_default": True, "is_active": True})
                return True

            return False
        except Exception:
            return False

    async def get_active_models(
        self,
        owner_id: str,
        include_deleted: bool = False
    ) -> List[Model]:
        """Get all active models for an owner"""
        query = {"owner_id": owner_id, "is_active": True}
        if not include_deleted:
            query["is_deleted"] = False

        return await self.model.find(query).to_list()

    async def count_by_owner(
        self,
        owner_id: str,
        include_deleted: bool = False
    ) -> int:
        """Count total models for an owner"""
        query = {"owner_id": owner_id}
        if not include_deleted:
            query["is_deleted"] = False

        return await self.model.find(query).count()

    async def get_stats(
        self,
        owner_id: str,
        include_deleted: bool = False
    ) -> Dict[str, int]:
        """Get model statistics for an owner"""
        base_query = {"owner_id": owner_id}
        if not include_deleted:
            base_query["is_deleted"] = False

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
