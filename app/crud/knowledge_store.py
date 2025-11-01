from app.crud.base import BaseCRUD
from app.models.knowledge_store import KnowledgeStore
from app.schemas.knowledge_store import KnowledgeStoreCreateRequest, KnowledgeStoreUpdateRequest
from typing import Optional, List, Dict, Any
from bson import ObjectId

class KnowledgeStoreCRUD(BaseCRUD[KnowledgeStore, KnowledgeStoreCreateRequest, KnowledgeStoreUpdateRequest]):
    def __init__(self):
        super().__init__(KnowledgeStore)

    async def get_by_owner_and_name(self, owner_id: str, name: str) -> Optional[KnowledgeStore]:
        """Get knowledge store by owner ID and name."""
        return await self.get_one(
            filter_={"owner_id": owner_id, "name": name},
            include_deleted=False
        )

    async def get_by_owner_and_id(self, owner_id: str, knowledge_store_id: str) -> Optional[KnowledgeStore]:
        """Get knowledge store by owner ID and ID."""
        return await self.get_one(
            filter_={"owner_id": owner_id, "_id": ObjectId(knowledge_store_id)},
            include_deleted=False
        )
    async def get_by_collection_name(self, collection_name: str) -> Optional[KnowledgeStore]:
        """Get knowledge store by collection name."""
        return await self.get_one(
            filter_={"collection_name": collection_name},
            include_deleted=False
        )

    async def list_by_owner(
        self,
        owner_id: str,
        limit: int = 50,
        skip: int = 0,
        status: Optional[str] = None
    ) -> List[KnowledgeStore]:
        """List knowledge stores by owner."""
        # Note: status filtering is handled in the service layer by checking Qdrant
        return await self.list(
            filter_={"owner_id": owner_id},
            limit=limit,
            skip=skip,
            include_deleted=False,
            owner_id=owner_id
        )

    async def get_by_owner_and_dimension(self, owner_id: str, dimension: int) -> List[KnowledgeStore]:
        """Get knowledge stores by owner ID and dimension."""
        return await self.list(
            filter_={"dimension": dimension, "owner_id": owner_id},
            include_deleted=False,
        )

# Global instance
knowledge_store_crud = KnowledgeStoreCRUD()
