from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.schemas.credential import ProviderList
from app.services.credential_service import CredentialService
from app.services.provider_service import ProviderService
from app.utils.verify_token import verify_token
from app.utils.api_response import ok
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("")
async def get_providers(
    active_only: bool = Query(True, description="Only return active providers")
):
    """Get all AI providers"""
    try:
        credential_service = CredentialService()
        result = await credential_service.get_providers(active_only)
        return ok(data=result, message="Providers retrieved successfully")
    except Exception as e:
        logger.error(f"Error retrieving providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve providers")


@router.post("/refresh")
async def refresh_providers(
    current_user = Depends(verify_token)
):
    """Refresh providers from YAML configuration"""
    try:
        count = await ProviderService.refresh_providers()
        return ok(data={"processed_count": count}, message=f"Successfully refreshed {count} providers")
    except Exception as e:
        logger.error(f"Error refreshing providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh providers")
