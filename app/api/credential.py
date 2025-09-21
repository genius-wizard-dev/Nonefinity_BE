from fastapi import APIRouter, Depends, HTTPException, Query, Path, Form
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from typing import Optional

from app.schemas.credential import (
    CredentialCreate, CredentialUpdate
)
from app.services.credential_service import CredentialService
from app.services import user_service
from app.core.exceptions import AppError
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def get_owner_and_service(current_user):
    """Helper function to get owner and credential service"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    owner_id = str(user.id)
    credential_service = CredentialService()

    return owner_id, credential_service


@router.post("")
async def create_credential(
    name: str = Form(...),
    provider_id: str = Form(...),
    api_key: str = Form(...),
    base_url: Optional[str] = Form(None),
    current_user = Depends(verify_token)
):
    """Create a new credential"""
    try:
        owner_id, credential_service = await get_owner_and_service(current_user)

        credential_data = CredentialCreate(
            name=name,
            provider_id=provider_id,
            api_key=api_key,
            base_url=base_url
        )

        result = await credential_service.create_credential(owner_id, credential_data)
        return created(data=result, message="Credential created successfully")

    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error creating credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to create credential")


@router.get("")
async def list_credentials(
    current_user = Depends(verify_token),
    skip: int = Query(0),
    limit: int = Query(100)
):
    """Get all credentials for the current user"""
    try:
        owner_id, credential_service = await get_owner_and_service(current_user)
        result = await credential_service.get_credentials(owner_id, skip, limit)
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
    name: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    current_user = Depends(verify_token)
):
    """Update a credential"""
    try:
        owner_id, credential_service = await get_owner_and_service(current_user)

        update_data = CredentialUpdate(
            name=name,
            api_key=api_key,
            base_url=base_url,
            is_active=is_active
        )

        # Check if any fields are provided
        if not any(v is not None for v in update_data.model_dump().values()):
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="No fields provided for update")

        result = await credential_service.update_credential(owner_id, credential_id, update_data)

        if not result:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Credential not found")

        return ok(data=result, message="Credential updated successfully")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to update credential")


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

        return ok(data={"credential_id": credential_id}, message="Credential deleted successfully")
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
    length: int = Form(32, description="Key length in bytes"),
    current_user = Depends(verify_token)
):
    """Generate a cryptographically secure key for CREDENTIAL_SECRET_KEY"""
    try:
        if length < 16 or length > 128:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Key length must be between 16 and 128 bytes"
            )

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
