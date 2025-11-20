from fastapi import APIRouter, Depends, Query, Path, Body, status, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from typing import Optional, List

from app.schemas.knowledge_store import (
    KnowledgeStoreCreateRequest,
    KnowledgeStoreUpdateRequest,
    KnowledgeStoreResponse,
    KnowledgeStoreListResponse,
    ScrollDataRequest,
    ScrollDataResponse,
    DeleteVectorsRequest
)
from app.schemas.response import ApiResponse, ApiError
from app.services.knowledge_store_service import KnowledgeStoreService
from app.services import user_service
from app.core.exceptions import AppError
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from app.utils import get_logger
from app.utils.cache_decorator import invalidate_cache

logger = get_logger(__name__)

router = APIRouter(
    tags=["Knowledge Stores"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)

async def get_owner_and_service(current_user):
    """Helper function to get owner and knowledge store service"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    owner_id = str(user.id)
    knowledge_store_service = KnowledgeStoreService()

    return owner_id, knowledge_store_service


@router.get(
    "/check-name/{name}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Check Knowledge Store Name",
    description="Check if a knowledge store name is available for the current user",
    responses={
        200: {"description": "Name availability checked successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def check_knowledge_store_name(
    name: str = Path(..., description="Knowledge store name to check"),
    current_user = Depends(verify_token)
):
    """Check if a knowledge store name is available."""
    try:
        owner_id, service = await get_owner_and_service(current_user)
        existing = await service._crud.get_by_owner_and_name(owner_id, name)
        is_available = existing is None

        return ok(
            data={"name": name, "available": is_available},
            message=f"Name '{name}' is {'available' if is_available else 'not available'}"
        )
    except Exception as e:
        logger.error(f"API: Error checking name availability: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check name availability")


@router.post(
    "",
    response_model=ApiResponse[KnowledgeStoreResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Knowledge Store",
    description="Create a new knowledge store with Qdrant collection",
    responses={
        201: {"description": "Knowledge store created successfully"},
        400: {"description": "Invalid request or collection creation failed"},
        401: {"description": "Authentication required"},
        409: {"description": "Knowledge store name already exists"},
        422: {"description": "Validation error"}
    }
)
@invalidate_cache("knowledge-stores")
async def create_knowledge_store(
    request: KnowledgeStoreCreateRequest,
    current_user = Depends(verify_token)
):
    """Create a new knowledge store."""
    try:
        owner_id, service = await get_owner_and_service(current_user)
        result = await service.create_knowledge_store(owner_id, request)
        return created(data=result, message="Knowledge store created successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"API: Unexpected error creating knowledge store: {str(e)}")
        import traceback
        logger.error(f"API: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to create knowledge store")


@router.get(
    "",
    response_model=ApiResponse[KnowledgeStoreListResponse],
    status_code=status.HTTP_200_OK,
    summary="List Knowledge Stores",
    description="Get a paginated list of knowledge stores for the current user with optional filtering",
    responses={
        200: {"description": "Knowledge stores retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def list_knowledge_stores(
    current_user = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List knowledge stores for the current user."""
    try:
        owner_id, service = await get_owner_and_service(current_user)
        result = await service.list_knowledge_stores(owner_id, limit, skip, status)
        return ok(data=result, message="Knowledge stores retrieved successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving knowledge stores: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve knowledge stores")


@router.get(
    "/{knowledge_store_id}",
    response_model=ApiResponse[KnowledgeStoreResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Knowledge Store",
    description="Get a specific knowledge store by ID",
    responses={
        200: {"description": "Knowledge store retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Knowledge store not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_knowledge_store(
    knowledge_store_id: str = Path(..., description="Knowledge store ID"),
    current_user = Depends(verify_token)
):
    """Get a specific knowledge store by ID."""
    try:
        owner_id, service = await get_owner_and_service(current_user)
        result = await service.get_knowledge_store(knowledge_store_id, owner_id)
        return ok(data=result, message="Knowledge store retrieved successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving knowledge store: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve knowledge store")


@router.put(
    "/{knowledge_store_id}",
    response_model=ApiResponse[KnowledgeStoreResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Knowledge Store",
    description="Update a knowledge store configuration",
    responses={
        200: {"description": "Knowledge store updated successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Knowledge store not found"},
        409: {"description": "Knowledge store name already exists"},
        500: {"description": "Internal server error"}
    }
)
@invalidate_cache("knowledge-stores")
async def update_knowledge_store(
    knowledge_store_id: str = Path(..., description="Knowledge store ID"),
    request: KnowledgeStoreUpdateRequest = Body(...),
    current_user = Depends(verify_token)
):
    """Update a knowledge store."""
    try:
        owner_id, service = await get_owner_and_service(current_user)
        result = await service.update_knowledge_store(knowledge_store_id, request, owner_id)
        return ok(data=result, message="Knowledge store updated successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating knowledge store: {e}")
        raise HTTPException(status_code=500, detail="Failed to update knowledge store")


@router.delete(
    "/{knowledge_store_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Knowledge Store",
    description="Delete a knowledge store and its Qdrant collection",
    responses={
        200: {"description": "Knowledge store deleted successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Knowledge store not found"},
        500: {"description": "Internal server error"}
    }
)
@invalidate_cache("knowledge-stores")
async def delete_knowledge_store(
    knowledge_store_id: str = Path(..., description="Knowledge store ID"),
    current_user = Depends(verify_token)
):
    """Delete a knowledge store."""
    try:
        owner_id, service = await get_owner_and_service(current_user)
        await service.delete_knowledge_store(knowledge_store_id, owner_id)
        return ok(message="Knowledge store deleted successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting knowledge store: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete knowledge store")


@router.get(
    "/{knowledge_store_id}/info",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get Collection Info",
    description="Get collection information from Qdrant",
    responses={
        200: {"description": "Collection info retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Knowledge store not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_collection_info(
    knowledge_store_id: str = Path(..., description="Knowledge store ID"),
    current_user = Depends(verify_token)
):
    """Get collection information from Qdrant."""
    try:
        owner_id, service = await get_owner_and_service(current_user)

        # Get collection info from Qdrant (this method handles ownership check internally)
        collection_info = await service.get_collection_info(knowledge_store_id, owner_id)
        if not collection_info:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Failed to get collection info")

        return ok(data=collection_info, message="Collection info retrieved successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving collection info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve collection info")


@router.post(
    "/{knowledge_store_id}/scroll-data",
    response_model=ApiResponse[ScrollDataResponse],
    status_code=status.HTTP_200_OK,
    summary="Scroll Data from Knowledge Store",
    description="Scroll through data in a knowledge store's Qdrant collection with pagination support",
    responses={
        200: {"description": "Data scrolled successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Knowledge store not found or access denied"},
        500: {"description": "Internal server error"}
    }
)
async def scroll_knowledge_store_data(
    knowledge_store_id: str = Path(..., description="Knowledge store ID"),
    request: ScrollDataRequest = Body(...),
    current_user = Depends(verify_token)
):
    """Scroll through data in a knowledge store's Qdrant collection with pagination."""
    try:
        owner_id, service = await get_owner_and_service(current_user)
        result = await service.scroll_data(knowledge_store_id, request, owner_id)
        return ok(data=result, message="Data scrolled successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error scrolling data: {e}")
        raise HTTPException(status_code=500, detail="Failed to scroll data")


@router.get(
  "/dimension/{dimension}",
  response_model=ApiResponse[List[KnowledgeStoreResponse]],
  status_code=status.HTTP_200_OK,
  summary="Get Knowledge Stores by Dimension",
  description="Get knowledge stores by dimension",
)
async def get_knowledge_store_dimension(
  dimension: int,
  current_user = Depends(verify_token)):
  try:
    owner_id, service = await get_owner_and_service(current_user)
    result = await service.get_knowledge_store_dimension(dimension, owner_id)
    return ok(data=result, message="Knowledge stores retrieved successfully")
  except HTTPException:
    raise
  except AppError as e:
    raise HTTPException(status_code=e.status_code, detail=e.message)
  except Exception as e:
    logger.error(f"Error retrieving knowledge store dimension: {e}")
    raise HTTPException(status_code=500, detail="Failed to retrieve knowledge store dimension")


@router.post(
    "/{knowledge_store_id}/delete-vectors",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete Vectors from Knowledge Store",
    description="Delete specific vectors/points from a knowledge store's Qdrant collection",
    responses={
        200: {"description": "Vectors deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied - not the owner"},
        404: {"description": "Knowledge store not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_vectors(
    knowledge_store_id: str = Path(..., description="Knowledge store ID"),
    request: DeleteVectorsRequest = Body(...),
    current_user = Depends(verify_token)
):
    """Delete specific vectors from a knowledge store. Only the owner can delete vectors."""
    try:
        owner_id, service = await get_owner_and_service(current_user)

        # Delete vectors (this will check ownership internally)
        deleted_count = await service.delete_vectors(knowledge_store_id, request.point_ids, owner_id)

        return ok(
            data={
                "deleted_count": deleted_count,
                "point_ids": request.point_ids
            },
            message=f"Successfully deleted {deleted_count} vector(s)"
        )
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting vectors: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to delete vectors")
