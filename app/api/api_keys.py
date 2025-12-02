"""API Key Management Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from app.schemas.api_key import (
    APIKeyCreate,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyListResponse,
    APIKeyUpdate,
)
from app.crud.api_key import api_key_crud
from app.services.user import user_service
from app.utils.verify_token import verify_token
from app.utils.api_response import ok, created
from app.schemas.response import ApiResponse, ApiError
from app.core.exceptions import AppError
from app.utils import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["API Keys"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)


async def get_owner_id(current_user: dict) -> str:
    """Helper to get owner ID from current user"""
    # API keys already contain owner_id in 'sub'
    if current_user.get("auth_type") == "api_key":
        return current_user.get("sub")

    # JWT tokens contain clerk_id in 'sub', need to look up user
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    return str(user.id)


@router.post(
    "",
    response_model=ApiResponse[APIKeyCreateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create API Key",
    description="Create a new API key for external integrations"
)
async def create_api_key(
    request: APIKeyCreate,
    current_user: dict = Depends(verify_token)
):
    """
    Create a new API key

    The API key will be returned only once. Store it securely!
    """
    try:
        owner_id = await get_owner_id(current_user)

        # Create the API key
        api_key_doc, actual_key = await api_key_crud.create(owner_id, request)

        # Prepare response with the actual key
        response_data = APIKeyCreateResponse(
            id=str(api_key_doc.id),
            name=api_key_doc.name,
            key_prefix=api_key_doc.key_prefix,
            is_active=api_key_doc.is_active,
            last_used_at=api_key_doc.last_used_at,
            expires_at=api_key_doc.expires_at,
            created_at=api_key_doc.created_at,
            updated_at=api_key_doc.updated_at,
            api_key=actual_key  # The actual key - only shown once
        )

        return created(
            data=response_data,
            message="API key created successfully. Save it securely - it won't be shown again!"
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Create API key failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "",
    response_model=ApiResponse[APIKeyListResponse],
    summary="List API Keys",
    description="Get all API keys for the current user"
)
async def list_api_keys(
    current_user: dict = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of keys to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Number of keys to return"),
    include_inactive: bool = Query(False, description="Include inactive keys")
):
    """List all API keys for the current user"""
    try:
        owner_id = await get_owner_id(current_user)

        # Get API keys
        api_keys = await api_key_crud.list(owner_id, skip, limit, include_inactive)
        total = await api_key_crud.count(owner_id, include_inactive)

        # Convert to response format
        key_responses = [
            APIKeyResponse(
                id=str(key.id),
                name=key.name,
                key_prefix=key.key_prefix,
                is_active=key.is_active,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
                created_at=key.created_at,
                updated_at=key.updated_at
            )
            for key in api_keys
        ]

        return ok(
            data=APIKeyListResponse(
                api_keys=key_responses,
                total=total,
                skip=skip,
                limit=limit
            ),
            message="API keys retrieved successfully"
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"List API keys failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{key_id}",
    response_model=ApiResponse[APIKeyResponse],
    summary="Get API Key",
    description="Get details of a specific API key"
)
async def get_api_key(
    key_id: str = Path(..., description="API Key ID"),
    current_user: dict = Depends(verify_token)
):
    """Get a specific API key by ID"""
    try:
        owner_id = await get_owner_id(current_user)

        api_key = await api_key_crud.get_by_id(key_id, owner_id)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        return ok(
            data=APIKeyResponse(
                id=str(api_key.id),
                name=api_key.name,
                key_prefix=api_key.key_prefix,
                is_active=api_key.is_active,
                last_used_at=api_key.last_used_at,
                expires_at=api_key.expires_at,
                created_at=api_key.created_at,
                updated_at=api_key.updated_at
            ),
            message="API key retrieved successfully"
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Get API key failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/{key_id}",
    response_model=ApiResponse[APIKeyResponse],
    summary="Update API Key",
    description="Update an API key's name or status"
)
async def update_api_key(
    request: APIKeyUpdate,
    key_id: str = Path(..., description="API Key ID"),
    current_user: dict = Depends(verify_token)
):
    """Update an API key"""
    try:
        owner_id = await get_owner_id(current_user)

        api_key = await api_key_crud.update(key_id, owner_id, request)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        return ok(
            data=APIKeyResponse(
                id=str(api_key.id),
                name=api_key.name,
                key_prefix=api_key.key_prefix,
                is_active=api_key.is_active,
                last_used_at=api_key.last_used_at,
                expires_at=api_key.expires_at,
                created_at=api_key.created_at,
                updated_at=api_key.updated_at
            ),
            message="API key updated successfully"
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Update API key failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/{key_id}/revoke",
    response_model=ApiResponse[APIKeyResponse],
    summary="Revoke API Key",
    description="Revoke an API key (set to inactive)"
)
async def revoke_api_key(
    key_id: str = Path(..., description="API Key ID"),
    current_user: dict = Depends(verify_token)
):
    """Revoke an API key"""
    try:
        owner_id = await get_owner_id(current_user)

        api_key = await api_key_crud.revoke(key_id, owner_id)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        return ok(
            data=APIKeyResponse(
                id=str(api_key.id),
                name=api_key.name,
                key_prefix=api_key.key_prefix,
                is_active=api_key.is_active,
                last_used_at=api_key.last_used_at,
                expires_at=api_key.expires_at,
                created_at=api_key.created_at,
                updated_at=api_key.updated_at
            ),
            message="API key revoked successfully"
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Revoke API key failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{key_id}",
    response_model=ApiResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete API Key",
    description="Permanently delete an API key"
)
async def delete_api_key(
    key_id: str = Path(..., description="API Key ID"),
    current_user: dict = Depends(verify_token)
):
    """Delete an API key permanently"""
    try:
        owner_id = await get_owner_id(current_user)

        success = await api_key_crud.delete(key_id, owner_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        return ok(data={}, message="API key deleted successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Delete API key failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
