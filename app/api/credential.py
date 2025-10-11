from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from typing import Optional
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.schemas.credential import (
    CredentialCreate, CredentialUpdate, SecureKeyRequest, CredentialDetail,
    CredentialList
)
from app.schemas.response import ApiResponse, ApiError
from app.services.credential_service import CredentialService
from app.services import user_service
from app.core.exceptions import AppError
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from app.utils import get_logger
from app.schemas.model import ModelType

logger = get_logger(__name__)

router = APIRouter(
    prefix="/credentials",
    tags=["Credentials"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)


async def get_owner_and_service(current_user):
    """Helper function to get owner and credential service"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    owner_id = str(user.id)
    credential_service = CredentialService()

    return owner_id, credential_service


@router.post(
    "",
    response_model=ApiResponse[CredentialDetail],
    status_code=status.HTTP_201_CREATED,
    summary="Create Credential",
    description="Create a new API credential for AI provider authentication",
    responses={
        201: {"description": "Credential created successfully"},
        400: {"description": "Invalid request or validation error"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"}
    }
)
async def create_credential(
    current_user = Depends(verify_token),
    credential_data: CredentialCreate = Body(..., description="Credential data")
):
    try:
        owner_id, credential_service = await get_owner_and_service(current_user)

        success = await credential_service.create_credential(owner_id, credential_data)

        if not success:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Failed to create credential")

        return created(message="Credential created successfully")
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating credential: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create credential")

@router.get(
    "",
    response_model=ApiResponse[CredentialList],
    status_code=status.HTTP_200_OK,
    summary="List Credentials",
    description="Get a paginated list of credentials for the current user with optional filtering",
    responses={
        200: {"description": "Credentials retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def list_credentials(
    current_user = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of items to return"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    task_type: Optional[ModelType] = Query(None, description="Filter by supported task type")
):
    """
    Get all credentials for the current user

    This endpoint retrieves a paginated list of API credentials owned by the authenticated user.
    Results can be filtered by active status and supported task type.

    **Query Parameters:**
    - **skip**: Number of items to skip (pagination)
    - **limit**: Number of items to return (1-100, default: 100)
    - **active**: Filter by active status (true/false)
    - **task_type**: Filter by supported task type (chat/embedding)

    **Returns:**
    - **credentials**: List of credential objects with masked API keys
    - **total**: Total number of credentials matching the criteria
    - **page**: Current page number
    - **size**: Number of items per page

    **Example Response:**
    ```json
    {
        "success": true,
        "message": "Credentials retrieved successfully",
        "data": {
            "credentials": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "name": "OpenAI Production Key",
                    "provider_id": "openai",
                    "api_key": "sk-***masked***",
                    "is_active": true,
                    "usage_count": 150,
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ],
            "total": 1,
            "page": 1,
            "size": 100
        }
    }
    ```
    """
    try:
        owner_id, credential_service = await get_owner_and_service(current_user)
        result = await credential_service.get_credentials(owner_id, skip, limit, active, task_type)
        return ok(data=result, message="Credentials retrieved successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve credentials")


@router.get("/{credential_id}")
async def get_credential(
    credential_id: str = Path(..., description="Credential ID"),
    current_user = Depends(verify_token)
):
    """Get a specific credential by ID"""
    try:
        owner_id, credential_service = await get_owner_and_service(current_user)
        result = await credential_service.get_credential(owner_id, credential_id)

        if not result:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Credential not found")

        return ok(data=result, message="Credential retrieved successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve credential")


@router.put("/{credential_id}")
async def update_credential(
    credential_id: str = Path(..., description="Credential ID"),
    update_data: CredentialUpdate = Body(..., description="Update data"),
    current_user = Depends(verify_token)
):
    """Update a credential"""
    try:

        owner_id, credential_service = await get_owner_and_service(current_user)

        success = await credential_service.update_credential(owner_id, credential_id, update_data)

        if not success:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Failed to update credential")

        return ok(message="Credential updated successfully")
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating credential: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update credential")



@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: str = Path(..., description="Credential ID"),
    current_user = Depends(verify_token)
):
    """Delete a credential"""
    try:
        owner_id, credential_service = await get_owner_and_service(current_user)
        success = await credential_service.delete_credential(owner_id, credential_id)

        if not success:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Credential not found")

        return ok( message="Credential deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete credential")



@router.get("/provider/{provider_name}")
async def get_credentials_by_provider(
    provider_name: str = Path(..., description="Provider name"),
    current_user = Depends(verify_token)
):
    """Get all credentials for a specific provider"""
    try:
        owner_id, credential_service = await get_owner_and_service(current_user)
        credentials = await credential_service.crud.get_by_provider(owner_id, provider_name)

        # Convert to response format
        from app.schemas.credential import Credential
        credential_list = [
            Credential(
                id=str(cred.id),
                name=cred.name,
                provider_name=cred.provider_name,
                base_url=cred.base_url,
                additional_headers=cred.additional_headers,
                is_active=cred.is_active,
                created_at=cred.created_at,
                updated_at=cred.updated_at
            )
            for cred in credentials
        ]

        result = {
            "credentials": credential_list,
            "total": len(credential_list),
            "provider_name": provider_name
        }

        return ok(data=result, message=f"Credentials for provider '{provider_name}' retrieved successfully")
    except Exception as e:
        logger.error(f"Error retrieving credentials for provider: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve credentials")


@router.get("/encryption/health")
async def check_encryption_health(
    current_user = Depends(verify_token)
):
    """Check encryption system health"""
    try:
        credential_service = CredentialService()
        result = credential_service.validate_encryption_health()

        if result["encryption_healthy"]:
            return ok(data=result, message="Encryption system is healthy")
        else:
            return ok(data=result, message="Encryption system has issues")

    except Exception as e:
        logger.error(f"Error checking encryption health: {e}")
        raise HTTPException(status_code=500, detail="Failed to check encryption health")


@router.post("/encryption/generate-key")
async def generate_secure_key(
    request: SecureKeyRequest,
    current_user = Depends(verify_token)
):
    """Generate a cryptographically secure key for CREDENTIAL_SECRET_KEY"""
    try:
        length = request.length

        from datetime import datetime
        secure_key = CredentialService.generate_secure_key(length)

        result = {
            "secure_key": secure_key,
            "length": length,
            "timestamp": datetime.utcnow().isoformat(),
            "recommendation": f"Set CREDENTIAL_SECRET_KEY={secure_key} in your .env file"
        }

        return ok(data=result, message="Secure key generated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating secure key: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate secure key")
