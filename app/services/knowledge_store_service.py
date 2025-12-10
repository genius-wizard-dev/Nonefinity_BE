from app.databases.qdrant import qdrant
from app.crud.task import task_crud
from app.schemas.knowledge_store import KnowledgeStoreCreateRequest, KnowledgeStoreUpdateRequest, KnowledgeStoreResponse, KnowledgeStoreListResponse, ScrollDataRequest, ScrollDataResponse
from qdrant_client.models import Distance
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from app.core.exceptions import AppError
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT
from app.utils import get_logger
from app.services import model_service, credential_service, provider_service
from app.crud import chat_config_crud,  knowledge_store_crud
import uuid
logger = get_logger(__name__)

class KnowledgeStoreService:
    def __init__(self):
        self._qdrant = qdrant
        self._crud = knowledge_store_crud
        self._model_service = model_service
        self._credential_service = credential_service
        self._provider_service = provider_service
        self._chat_config_crud = chat_config_crud

    def _create_name_collection(self, name: str) -> str:
        """Create a name for a knowledge store."""
        return f"{name}-{uuid.uuid4().hex[:8]}"

    async def create_knowledge_store(self, owner_id: str, request: KnowledgeStoreCreateRequest) -> KnowledgeStoreResponse:
        """Create a new knowledge store."""
        try:
            # Check if knowledge store with same name exists for owner
            existing = await self._crud.get_by_owner_and_name(owner_id, request.name)
            if existing:
                raise HTTPException(
                    status_code=HTTP_409_CONFLICT,
                    detail=f"Knowledge store with name '{request.name}' already exists. Please choose a different name."
                )

            # Generate collection name
            collection_name = self._create_name_collection(request.name)

            # Create collection in Qdrant
            success = self._qdrant .create_collection(
                collection_name=collection_name,
                vector_size=request.dimension.value,
                distance=request.distance
            )

            if not success:
                logger.error(f"Failed to create Qdrant collection: {collection_name}")
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="Failed to create collection in Qdrant"
            )

            qdrant_info = self._qdrant .get_collection_info(collection_name)
            if not qdrant_info:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="Failed to get collection info from Qdrant"
                )

            # Create knowledge store record in database
            knowledge_store_data = {
                "name": request.name,
                "description": request.description,
                "owner_id": owner_id,
                "collection_name": collection_name,
                "dimension": request.dimension.value,
                "distance": request.distance.value,
            }

            knowledge_store = await self._crud.create(knowledge_store_data)

            # Get status from Qdrant for the response
            status = qdrant_info["status"]
            points_count = qdrant_info["points_count"] if qdrant_info else 0

            # Create response with all fields including status
            # New knowledge store is not in use yet
            result = KnowledgeStoreResponse(
                id=str(knowledge_store.id),
                name=knowledge_store.name,
                description=knowledge_store.description,
                dimension=knowledge_store.dimension,
                distance=knowledge_store.distance,
                status=status,
                created_at=knowledge_store.created_at,
                updated_at=knowledge_store.updated_at,
                points_count=points_count,
                is_use=False
            )
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during knowledge store creation: {str(e)}")
            logger.error(f"Request data: {request.model_dump()}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Failed to create knowledge store: {str(e)}"
            )

    async def get_knowledge_store(self, knowledge_store_id: str, owner_id: str) -> KnowledgeStoreResponse:
        """Get a knowledge store by ID."""
        knowledge_store = await self._crud.get_by_id(knowledge_store_id, owner_id=owner_id)
        if not knowledge_store:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Knowledge store not found"
            )

        # Get status from Qdrant
        qdrant_info = self._qdrant .get_collection_info(knowledge_store.collection_name)
        status = qdrant_info["status"] if qdrant_info else "unknown"
        points_count = qdrant_info["points_count"] if qdrant_info else 0

        # Check if knowledge store is being used in chat configs
        chat_configs = await self._chat_config_crud.get_by_knowledge_store_id(
            knowledge_store_id=str(knowledge_store.id),
            owner_id=owner_id
        )
        is_use = len(chat_configs) > 0

        result = KnowledgeStoreResponse(
            id=str(knowledge_store.id),
            name=knowledge_store.name,
            description=knowledge_store.description,
            dimension=knowledge_store.dimension,
            distance=knowledge_store.distance,
            status=status,
            created_at=knowledge_store.created_at,
            updated_at=knowledge_store.updated_at,
            points_count=points_count,
            is_use=is_use
        )
        return result

    async def list_knowledge_stores(
        self,
        owner_id: str,
        limit: int = 50,
        skip: int = 0,
        status: Optional[str] = None
    ) -> KnowledgeStoreListResponse:
        """List knowledge stores for an owner."""
        knowledge_stores = await self._crud.list_by_owner(
            owner_id=owner_id,
            limit=limit,
            skip=skip,
            status=status
        )

        # Get status from Qdrant for each knowledge store
        knowledge_store_responses = []
        for ks in knowledge_stores:
            qdrant_info = self._qdrant .get_collection_info(ks.collection_name)
            current_status = qdrant_info["status"] if qdrant_info else "unknown"
            points_count = qdrant_info["points_count"] if qdrant_info else 0

            # Check if knowledge store is being used in chat configs
            chat_configs = await self._chat_config_crud.get_by_knowledge_store_id(
                knowledge_store_id=str(ks.id),
                owner_id=owner_id
            )
            is_use = len(chat_configs) > 0

            # If status filter is provided, only include matching knowledge stores
            if status is None or current_status == status:
                result = KnowledgeStoreResponse(
                    id=str(ks.id),
                    name=ks.name,
                    description=ks.description,
                    dimension=ks.dimension,
                    distance=ks.distance,
                    status=current_status,
                    created_at=ks.created_at,
                    updated_at=ks.updated_at,
                    points_count=points_count,
                    is_use=is_use
                )
                knowledge_store_responses.append(result)

        # Get total count (all knowledge stores for owner, not filtered by status)
        total = len(await self._crud.list_by_owner(owner_id=owner_id))

        return KnowledgeStoreListResponse(
            knowledge_stores=knowledge_store_responses,
            total=total,
            limit=limit,
            skip=skip
        )

    async def update_knowledge_store(
        self,
        knowledge_store_id: str,
        request: KnowledgeStoreUpdateRequest,
        owner_id: str
    ) -> KnowledgeStoreResponse:
        """Update a knowledge store."""
        knowledge_store = await self._crud.get_by_id(knowledge_store_id, owner_id=owner_id)
        if not knowledge_store:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Knowledge store not found"
            )

        # Check if new name conflicts with existing knowledge store
        if request.name and request.name != knowledge_store.name:
            existing = await self._crud.get_by_owner_and_name(owner_id, request.name)
            if existing and existing.id != knowledge_store_id:
                raise HTTPException(
                    status_code=HTTP_409_CONFLICT,
                    detail="Knowledge store with this name already exists"
                )

        updated_knowledge_store = await self._crud.update(knowledge_store, request)

        # Get status from Qdrant
        qdrant_info = self._qdrant .get_collection_info(updated_knowledge_store.collection_name)
        status = qdrant_info["status"] if qdrant_info else "unknown"
        points_count = qdrant_info["points_count"] if qdrant_info else 0

        # Check if knowledge store is being used in chat configs
        chat_configs = await self._chat_config_crud.get_by_knowledge_store_id(
            knowledge_store_id=str(updated_knowledge_store.id),
            owner_id=owner_id
        )
        is_use = len(chat_configs) > 0

        result = KnowledgeStoreResponse(
            id=str(updated_knowledge_store.id),
            name=updated_knowledge_store.name,
            description=updated_knowledge_store.description,
            dimension=updated_knowledge_store.dimension,
            distance=updated_knowledge_store.distance,
            status=status,
            created_at=updated_knowledge_store.created_at,
            updated_at=updated_knowledge_store.updated_at,
            points_count=points_count,
            is_use=is_use
        )
        return result

    async def delete_knowledge_store(self, knowledge_store_id: str, owner_id: str) -> bool:
        """Delete a knowledge store and all related tasks."""
        knowledge_store = await self._crud.get_by_id(knowledge_store_id, owner_id=owner_id)
        if not knowledge_store:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Knowledge store not found"
            )
        # INSERT_YOUR_CODE
        # Check if this knowledge_store is used in any chat config
        chat_config_in_use = await self._chat_config_crud.get_by_knowledge_store_id(knowledge_store_id=knowledge_store_id, owner_id=owner_id)
        if chat_config_in_use:
            chat_names = [chat.name for chat in chat_config_in_use]
            raise AppError(
                message=f"Cannot delete knowledge store because it is used in the following chats: {', '.join(chat_names)}",
                status_code=HTTP_409_CONFLICT
            )

        # Delete all related tasks from MongoDB
        try:
            deleted_count = await task_crud.delete_by_knowledge_store_id(knowledge_store_id, owner_id)
            logger.info(f"Deleted {deleted_count} task(s) related to knowledge store {knowledge_store_id}")
        except Exception as e:
            logger.warning(f"Failed to delete related tasks for knowledge store {knowledge_store_id}: {e}")
            # Continue with knowledge store deletion even if task deletion fails

        # Delete collection from Qdrant
        success = self._qdrant .delete_collection(knowledge_store.collection_name)
        if not success:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Failed to delete collection from Qdrant"
            )

        # Hard delete the knowledge store record from database
        await self._crud.delete(knowledge_store)
        return True

    def create_collection(self, collection_name: str, vector_size: int = 384, distance: Distance = Distance.COSINE) -> bool:
        """Create a collection in Qdrant."""
        return self._qdrant .create_collection(collection_name, vector_size, distance)

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection from Qdrant."""
        return self._qdrant .delete_collection(collection_name)

    async def get_collection_info(self, knowledge_store_id: str, owner_id: str) -> Dict[str, Any]:
        """
        Get collection information from Qdrant, but return the 'name' from DB (not collection_name).
        """
        # Get the knowledge store from database
        knowledge_store = await self._crud.get_by_id(knowledge_store_id, owner_id=owner_id)
        if not knowledge_store:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="Knowledge store not found"
            )

        # Get info from Qdrant
        qdrant_info = self._qdrant .get_collection_info(knowledge_store.collection_name)

        if not qdrant_info:
            return None

        # Replace name in qdrant_info with name from DB
        qdrant_info["name"] = knowledge_store.name
        # Remove 'collection_name' if present (prevent showing it to user)
        qdrant_info.pop("collection_name", None)

        return qdrant_info

    async def scroll_data(self, knowledge_store_id: str, request: ScrollDataRequest, owner_id: str) -> ScrollDataResponse:
        """
        Scroll through data in a Qdrant collection with pagination.
        """
        try:
            # Get knowledge store by ID and verify ownership
            knowledge_store = await self._crud.get_by_id(knowledge_store_id, owner_id=owner_id)
            if not knowledge_store:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail="Knowledge store not found or access denied"
                )

            # Perform scroll operation using collection_name from knowledge store
            result = self._qdrant .scroll(
                collection_name=knowledge_store.collection_name,
                limit=request.limit,
                offset=request.scroll_id
            )

            points, next_scroll_id = result
            # Convert points to dictionaries for JSON serialization
            points_data = []
            for point in points:
                point_dict = {
                    "id": point.id,
                    "text": point.payload.get("page_content", "") if point.payload else "",
                    "vector": point.vector
                }
                points_data.append(point_dict)

            return ScrollDataResponse(
                points=points_data,
                scroll_id=next_scroll_id,
                has_more=next_scroll_id is not None,
                total_scrolled=len(points_data)
            )

        except Exception as e:
            logger.error(f"Error scrolling data: {str(e)}")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Failed to scroll data: {str(e)}"
            )

    async def get_knowledge_store_dimension(self, dimension: int, owner_id: str) -> List[KnowledgeStoreResponse]:
        """Get knowledge stores by dimension."""
        knowledge_stores = await self._crud.get_by_owner_and_dimension(owner_id, dimension)
        if not knowledge_stores:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail="No knowledge stores found with this dimension"
            )

        # Get status from Qdrant for each knowledge store
        knowledge_store_responses = []
        for ks in knowledge_stores:
            qdrant_info = self._qdrant .get_collection_info(ks.collection_name)
            status = qdrant_info["status"] if qdrant_info else "unknown"
            points_count = qdrant_info["points_count"] if qdrant_info else 0

            # Check if knowledge store is being used in chat configs
            chat_configs = await self._chat_config_crud.get_by_knowledge_store_id(
                knowledge_store_id=str(ks.id),
                owner_id=owner_id
            )
            is_use = len(chat_configs) > 0

            result = KnowledgeStoreResponse(
                id=str(ks.id),
                name=ks.name,
                description=ks.description,
                dimension=ks.dimension,
                distance=ks.distance,
                status=status,
                created_at=ks.created_at,
                updated_at=ks.updated_at,
                points_count=points_count,
                is_use=is_use
            )
            knowledge_store_responses.append(result)

        return knowledge_store_responses

    async def delete_vectors(self, knowledge_store_id: str, point_ids: List[str], owner_id: str) -> int:
        """
        Delete specific vectors/points from a knowledge store's Qdrant collection.
        Only the owner can delete vectors.

        Args:
            knowledge_store_id: The knowledge store ID
            point_ids: List of point IDs to delete
            owner_id: The owner's user ID

        Returns:
            Number of vectors deleted

        Raises:
            HTTPException: If knowledge store not found or access denied
        """
        try:
            # Get knowledge store and verify ownership
            knowledge_store = await self._crud.get_by_id(knowledge_store_id, owner_id=owner_id)
            if not knowledge_store:
                raise HTTPException(
                    status_code=HTTP_404_NOT_FOUND,
                    detail="Knowledge store not found or access denied"
                )

            # Verify that the knowledge store belongs to the user
            if knowledge_store.owner_id != owner_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied - you don't own this knowledge store"
                )

            # Delete points from Qdrant collection
            success = self._qdrant .delete_documents(
                ids=point_ids,
                collection_name=knowledge_store.collection_name
            )

            if not success:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST,
                    detail="Failed to delete vectors from Qdrant"
                )

            logger.info(f"Successfully deleted {len(point_ids)} vectors from knowledge store {knowledge_store_id}")
            return len(point_ids)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Failed to delete vectors: {str(e)}"
            )




knowledge_store_service = KnowledgeStoreService()
