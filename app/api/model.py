from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from typing import Optional

from app.schemas.model import ModelCreate, ModelType, ModelCreateRequest, ModelUpdateRequest, ModelResponse, ModelListResponse
from app.schemas.response import ApiResponse, ApiError
from app.services.model_service import ModelService
from app.services import user_service
from app.core.exceptions import AppError
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from app.utils import get_logger
from app.utils.cache_decorator import invalidate_cache

logger = get_logger(__name__)

router = APIRouter(
    tags=["AI Models"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)



async def get_owner_and_service(current_user):
    """Helper function to get owner and model service"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    owner_id = str(user.id)
    model_service = ModelService()

    return owner_id, model_service


@router.post(
    "",
    response_model=ApiResponse[ModelResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create AI Model",
    description="Create a new AI model configuration for chat or embedding tasks",
    responses={
        201: {"description": "Model created successfully"},
        400: {"description": "Invalid request or credential not found"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"}
    }
)
async def create_model(
    request: ModelCreateRequest,
    current_user = Depends(verify_token)
):

    try:
        owner_id, model_service = await get_owner_and_service(current_user)

        model_data = ModelCreate(
            credential_id=request.credential_id,
            name=request.name,
            model=request.model,
            type=request.type,
            description=request.description,
            is_active=request.is_active,
        )

        success = await model_service.create_model(owner_id, model_data)
        if not success:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Failed to create model")

        return created(message="Model created successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating model: {e}")
        raise HTTPException(status_code=500, detail="Failed to create model")


@router.get(
    "",
    response_model=ApiResponse[ModelListResponse],
    status_code=status.HTTP_200_OK,
    summary="List AI Models",
    description="Get a paginated list of AI models for the current user with optional filtering",
    responses={
        200: {"description": "Models retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def list_models(
    current_user = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    type: Optional[ModelType] = Query(None, description="Filter by model type (chat or embedding)"),
    credential_id: Optional[str] = Query(None, description="Filter by credential ID"),
    active_only: bool = Query(False, description="Show only active models")
):
    """
    Get all models for the current user

    This endpoint retrieves a paginated list of AI models owned by the authenticated user.
    Results can be filtered by type, credential, and active status.

    **Query Parameters:**
    - **skip**: Number of items to skip (pagination)
    - **limit**: Number of items to return (1-100, default: 50)
    - **type**: Filter by model type (chat or embedding)
    - **credential_id**: Filter by specific credential ID
    - **active_only**: Show only active models (default: false)

    **Returns:**
    - **models**: List of model objects with complete metadata
    - **total**: Total number of models matching the criteria
    - **skip**: Number of items skipped
    - **limit**: Number of items per page

    **Example Response:**
    ```json
    {
        "success": true,
        "message": "Models retrieved successfully",
        "data": {
            "models": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "name": "GPT-4 Chat Model",
                    "model": "gpt-4",
                    "type": "chat",
                    "is_active": true,
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ],
            "total": 1,
            "skip": 0,
            "limit": 50
        }
    }
    ```
    """
    try:

        owner_id, model_service = await get_owner_and_service(current_user)
        result = await model_service.get_models(
            owner_id=owner_id,
            skip=skip,
            limit=limit,
            model_type=type,
            credential_id=credential_id,
            active_only=active_only
        )
        return ok(data=result, message="Models retrieved successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving models: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve models")


@router.get("/stats")
async def get_model_stats(
    current_user = Depends(verify_token)
):
    """Get model statistics for the current user"""
    try:
        owner_id, model_service = await get_owner_and_service(current_user)
        result = await model_service.get_model_stats(owner_id)
        return ok(data=result, message="Model statistics retrieved successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving model statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve model statistics")


@router.get("/default/{model_type}")
async def get_default_model(
    model_type: ModelType = Path(..., description="Model type (chat or embedding)"),
    current_user = Depends(verify_token)
):
    """Get the default model for a specific type"""
    try:
        owner_id, model_service = await get_owner_and_service(current_user)
        result = await model_service.get_default_model(owner_id, model_type)

        if not result:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"No default {model_type} model found"
            )

        return ok(data=result, message=f"Default {model_type} model retrieved successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving default model: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve default model")


@router.get("/{model_id}")
async def get_model(
    model_id: str = Path(..., description="Model ID"),
    current_user = Depends(verify_token)
):
    """Get a specific model by ID"""
    try:
        owner_id, model_service = await get_owner_and_service(current_user)
        result = await model_service.get_model(owner_id, model_id)

        if not result:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Model not found")

        return ok(data=result, message="Model retrieved successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving model: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve model")


@router.put("/{model_id}")
@invalidate_cache("models")
async def update_model(
    model_id: str = Path(..., description="Model ID"),
    request: ModelUpdateRequest = Body(...),
    current_user = Depends(verify_token)
):
    """Update a model configuration"""
    try:
        owner_id, model_service = await get_owner_and_service(current_user)

        success = await model_service.update_model(owner_id, model_id, request)

        if not success:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Model not found or update failed")

        return ok(message="Model updated successfully")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating model: {e}")
        raise HTTPException(status_code=500, detail="Failed to update model")


@router.delete("/{model_id}")
@invalidate_cache("models")
async def delete_model(
    model_id: str = Path(..., description="Model ID"),
    current_user = Depends(verify_token)
):
    """Delete a model configuration"""
    try:
        owner_id, model_service = await get_owner_and_service(current_user)
        success = await model_service.delete_model(owner_id, model_id)

        if not success:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Model not found")

        return ok(message="Model deleted successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete model")


@router.post("/{model_id}/set-default")
@invalidate_cache("models")
async def set_default_model(
    model_id: str = Path(..., description="Model ID"),
    current_user = Depends(verify_token)
):
    """Set a model as the default for its type"""
    try:
        owner_id, model_service = await get_owner_and_service(current_user)
        success = await model_service.set_default_model(owner_id, model_id)

        if not success:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Model not found or failed to set as default")

        return ok(message="Model set as default successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default model: {e}")
        raise HTTPException(status_code=500, detail="Failed to set default model")


@router.get("/by-credential/{credential_id}")
async def get_models_by_credential(
    credential_id: str = Path(..., description="Credential ID"),
    current_user = Depends(verify_token)
):
    """Get all models for a specific credential"""
    try:
        owner_id, model_service = await get_owner_and_service(current_user)
        result = await model_service.get_models(
            owner_id=owner_id,
            credential_id=credential_id,
            skip=0,
            limit=100
        )

        return ok(data=result, message=f"Models for credential '{credential_id}' retrieved successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving models for credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve models")
