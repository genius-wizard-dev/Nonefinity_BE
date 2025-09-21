from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from bson import ObjectId
from beanie import Document
from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=Document)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class BaseCRUD(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    def __init__(self, model: Type[ModelT]):
        self.model = model

    async def get_by_id(self, id: str, include_deleted: bool = True) -> Optional[ModelT]:
        query = {"_id": ObjectId(id)}
        if not include_deleted and "is_deleted" in self.model.__fields__:
            query["is_deleted"] = False
        return await self.model.find_one(query)

    async def get_one(
        self, filter_: Dict[str, Any], include_deleted: bool = True
    ) -> Optional[ModelT]:
        query = dict(filter_)
        if not include_deleted and "is_deleted" in self.model.__fields__:
            query["is_deleted"] = False
        return await self.model.find_one(query)

    async def list(
        self,
        filter_: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        skip: int = 0,
        include_deleted: bool = True,
    ) -> List[ModelT]:
        query = dict(filter_ or {})
        if not include_deleted and "is_deleted" in self.model.__fields__:
            query["is_deleted"] = False
        cursor = self.model.find(query)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return await cursor.to_list()

    async def create(self, obj_in: CreateSchemaT) -> ModelT:
        data = obj_in.model_dump()
        if "is_deleted" in self.model.__fields__:
            data.setdefault("is_deleted", False)
            data.setdefault("deleted_at", None)
        db_obj = self.model(**data)
        await db_obj.insert()
        return db_obj

    async def update(
        self,
        db_obj: ModelT,
        obj_in: UpdateSchemaT | Dict[str, Any],
    ) -> ModelT:
        if isinstance(obj_in, BaseModel):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = {k: v for k, v in obj_in.items() if v is not None}

        if "updated_at" in db_obj.__fields__:
            update_data["updated_at"] = datetime.utcnow()

        await db_obj.set(update_data)
        return db_obj

    async def soft_delete(self, db_obj: ModelT, soft_delete: bool = True) -> None:
        if soft_delete and "is_deleted" in db_obj.__fields__:
            payload = {"is_deleted": True, "deleted_at": datetime.utcnow()}
            if "updated_at" in db_obj.__fields__:
                payload["updated_at"] = datetime.utcnow()
            await db_obj.set(payload)
        else:
            await db_obj.delete()

    async def delete(self, db_obj: ModelT) -> None:
        await db_obj.delete()
