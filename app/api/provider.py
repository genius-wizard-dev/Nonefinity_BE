from fastapi import APIRouter, HTTPException, Query, Path, status

from app.schemas.provider import ProviderList, ProviderResponse, ProviderTaskConfigResponse
from app.schemas.response import ApiResponse, ApiError
from app.services.credential_service import CredentialService
from app.services.provider_service import ProviderService
from app.utils.api_response import ok
from app.utils import get_logger
from app.utils.cache_decorator import cache_list
from app.schemas.model import ModelType

logger = get_logger(__name__)

router = APIRouter(
    tags=["AI Providers"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)


@cache_list("providers", ttl=300)
@router.get(
    "",
    response_model=ApiResponse[ProviderList],
    status_code=status.HTTP_200_OK,
    summary="List AI Providers",
    description="Get a list of all available AI providers with their capabilities and configuration",
    responses={
        200: {"description": "Providers retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
async def get_providers(
    active_only: bool = Query(True, description="Only return active providers")
):
    """
    ```
    """
    try:
        credential_service = CredentialService()
        result = await credential_service.get_providers(active_only)
        return ok(data=result, message="Providers retrieved successfully")
    except Exception as e:
        logger.error(f"Error retrieving providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve providers")


@router.get("/task/{task_type}")
@cache_list("providers", ttl=300)
async def get_providers_by_task(
    task_type: ModelType = Path(..., description="Task type (e.g., chat, embedding, moderation)"),
    active_only: bool = Query(True, description="Only return active providers")
):
    """Get providers that support a specific task type"""
    try:
        providers = await ProviderService.get_providers_by_task(task_type, active_only)
        provider_responses = [
            ProviderResponse(
                id=str(provider.id),
                provider=provider.provider,
                name=provider.name,
                description=provider.description,
                base_url=provider.base_url,
                logo_url=provider.logo_url,
                docs_url=provider.docs_url,
                models_url=provider.models_url,
                api_key_header=provider.api_key_header,
                api_key_prefix=provider.api_key_prefix,
                is_active=provider.is_active,
                support=provider.support,
                tags=provider.tags,
                created_at=provider.created_at,
                updated_at=provider.updated_at
            )
            for provider in providers
        ]
        result = ProviderList(providers=provider_responses, total=len(provider_responses))
        return ok(data=result, message=f"Providers supporting '{task_type}' retrieved successfully")
    except Exception as e:
        logger.error(f"Error retrieving providers for task '{task_type}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve providers for task '{task_type}'")


@router.get("/{provider_name}")
@cache_list("providers", ttl=300)
async def get_provider_details(
    provider_name: str = Path(..., description="Provider name"),
    active_only: bool = Query(True, description="Only return if provider is active")
):
    """Get detailed information about a specific provider"""
    try:
        provider = await ProviderService.get_provider_by_name(provider_name, active_only)
        result = ProviderResponse(
            id=str(provider.id),
            provider=provider.provider,
            name=provider.name,
            description=provider.description,
            base_url=provider.base_url,
            logo_url=provider.logo_url,
            docs_url=provider.docs_url,
            models_url=provider.models_url,
            api_key_header=provider.api_key_header,
            api_key_prefix=provider.api_key_prefix,
            is_active=provider.is_active,
            support=provider.support,
            tags=provider.tags,
            created_at=provider.created_at,
            updated_at=provider.updated_at
        )
        return ok(data=result, message=f"Provider '{provider_name}' retrieved successfully")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving provider '{provider_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve provider '{provider_name}'")


@router.get("/{provider_name}/tasks/{task_type}")
@cache_list("providers", ttl=300)
async def get_provider_task_config(
    provider_name: str = Path(..., description="Provider name"),
    task_type: ModelType = Path(..., description="Task type")
):
    """Get task configuration for a specific provider and task type"""
    try:
        config = await ProviderService.get_provider_task_config(provider_name, task_type)
        if not config:
            raise HTTPException(status_code=404, detail=f"No configuration found for task '{task_type}' in provider '{provider_name}'")

        result = ProviderTaskConfigResponse(
            task_type=task_type,
            class_path=config.get('class_path', ''),
            init_params=config.get('init_params', []),
            provider=provider_name
        )
        return ok(data=result, message=f"Task configuration for '{provider_name}:{task_type}' retrieved successfully")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving task config for '{provider_name}:{task_type}': {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve task configuration")
