from typing import Optional, Dict, Any

from app.crud.model import ModelCRUD
from app.crud.credential import CredentialCRUD
from app.models.model import Model, ModelType
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse, ModelStats, ModelUpdateRequest
from app.core.exceptions import AppError
from app.utils.logging import get_logger
from app.services.credential_service import CredentialService
import aiohttp

logger = get_logger(__name__)

class ModelService:
    def __init__(self):
        self.crud = ModelCRUD()
        self.credential_crud = CredentialCRUD()
        self.credential_service = CredentialService()


    async def _check_model(self, model: str, base_url: str, additional_headers: Optional[Dict[str, str]] = None) -> tuple[bool, str]:
        """
        Check if a model exists by calling the provider's list_models_url/model endpoint.
        Returns a tuple of (success, error_message).
        """
        url = f"{base_url}/models/{model}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10, headers=additional_headers) as resp:
                    if resp.status == 200:
                        return True, ""
                    # Try to parse error response
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    if (
                        resp.status == 404 or
                        (
                            isinstance(data, dict)
                            and "error" in data
                            and data["error"].get("code") == "model_not_found"
                        )
                    ):
                        error_msg = data.get("error", {}).get("message", "Model not found")
                        logger.error(f"Model check failed: {error_msg}")
                        return False, error_msg
                    # Other errors
                    error_text = await resp.text()
                    logger.error(f"Unexpected error when checking model: {error_text}")
                    return False, f"Unexpected error: {error_text}"
        except Exception as e:
            logger.error(f"Exception during model check: {str(e)}")
            return False, str(e)


    async def create_model(self, owner_id: str, model_data: ModelCreate) -> bool:
        """Create a new AI model configuration"""
        try:
            # Validate credential exists and belongs to user
            credential = await self.credential_crud.get_by_owner_and_id(
                owner_id, model_data.credential_id
            )
            if not credential:
                logger.error(f"Credential not found for user {owner_id}")
                return False

            # Check if model name already exists for this owner
            if await self.crud.check_name_exists(owner_id, model_data.name):
                logger.error(f"Model name '{model_data.name}' already exists for user {owner_id}")
                return False
            api_key = self.credential_service._decrypt_api_key(credential.api_key)
            headers = credential.additional_headers or {}
            headers["Authorization"] = f"Bearer {api_key}"
            model_exists, error_message = await self._check_model(model_data.model, credential.base_url, headers)
            if not model_exists:
                logger.error(f"Model {model_data.model} not found for user {owner_id}: {error_message}")
                raise AppError(message=error_message)

            # Create the model
            model = await self.crud.create_with_owner(owner_id, model_data)

            logger.info(f"Model created successfully for user {owner_id}")
            return True

        except AppError:
            # Re-raise AppError to preserve the specific error message
            raise
        except Exception as e:
            logger.error(f"Failed to create model for user {owner_id}: {str(e)}")
            return False

    async def get_models(
        self,
        owner_id: str,
        skip: int = 0,
        limit: int = 50,
        model_type: Optional[ModelType] = None,
        credential_id: Optional[str] = None,
        active_only: bool = False
    ) -> Dict[str, Any]:
        """Get models for a user with filtering options"""
        try:
            # Use the new CRUD method with all filters applied at MongoDB level
            models = await self.crud.get_models_with_filters(
                owner_id=owner_id,
                skip=skip,
                limit=limit,
                model_type=model_type,
                credential_id=credential_id,
                active_only=active_only
            )

            # Get total count with the same filters
            total = await self.crud.count_models_with_filters(
                owner_id=owner_id,
                model_type=model_type,
                credential_id=credential_id,
                active_only=active_only
            )

            model_responses = [self._to_response(model) for model in models]
            logger.debug(f"Models retrieved successfully: {model_responses}")

            return {
                "models": model_responses,
                "total": total,
                "skip": skip,
                "limit": limit
            }

        except Exception as e:
            raise AppError(
                message=f"Failed to retrieve models: {str(e)}",
                status_code=500
            )

    async def get_model(self, owner_id: str, model_id: str) -> Optional[ModelResponse]:
        """Get a specific model by ID"""
        try:
            model = await self.crud.get_by_owner_and_id(owner_id, model_id)
            if not model:
                return None

            return self._to_response(model)

        except Exception as e:
            raise AppError(
                message=f"Failed to retrieve model: {str(e)}",
                status_code=500
            )

    async def update_model(
        self,
        owner_id: str,
        model_id: str,
        update_data: ModelUpdateRequest
    ) -> bool:
        """Update a model configuration"""
        try:
            # Get existing model
            model = await self.crud.get_by_owner_and_id(owner_id, model_id)
            if not model:
                logger.error(f"Model {model_id} not found for user {owner_id}")
                return False

            # Check name uniqueness if name is being updated
            if update_data.name and update_data.name != model.name:
                if await self.crud.check_name_exists(owner_id, update_data.name, model_id):
                    logger.error(f"Model name '{update_data.name}' already exists for user {owner_id}")
                    return False


            # Update the model
            await self.crud.update(model, update_data)
            logger.info(f"Model {model_id} updated successfully for user {owner_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update model {model_id} for user {owner_id}: {str(e)}")
            return False

    async def delete_model(self, owner_id: str, model_id: str) -> bool:
        """Delete a model (soft delete)"""
        try:
            model = await self.crud.get_by_owner_and_id(owner_id, model_id)
            if not model:
                return False

            await self.crud.delete(model)
            return True

        except Exception as e:
            raise AppError(
                message=f"Failed to delete model: {str(e)}",
                status_code=500
            )


    async def get_model_stats(self, owner_id: str) -> ModelStats:
        """Get model statistics for a user"""
        try:
            stats = await self.crud.get_stats(owner_id)
            return ModelStats(**stats)

        except Exception as e:
            raise AppError(
                message=f"Failed to get model statistics: {str(e)}",
                status_code=500
            )

    def _to_response(self, model: Model) -> ModelResponse:
        """Convert model to response format"""
        return ModelResponse(
            id=str(model.id),
            owner_id=model.owner_id,
            credential_id=model.credential_id,
            name=model.name,
            model=model.model,
            type=model.type,
            description=model.description,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
