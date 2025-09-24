from typing import Optional, Dict, Any

from app.crud.model import ModelCRUD
from app.crud.credential import CredentialCRUD
from app.models.model import Model, ModelType
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse, ModelStats
from app.core.exceptions import AppError
from app.utils.logging import get_logger

logger = get_logger(__name__)

class ModelService:
    def __init__(self):
        self.crud = ModelCRUD()
        self.credential_crud = CredentialCRUD()

    async def create_model(self, owner_id: str, model_data: ModelCreate) -> ModelResponse:
        """Create a new AI model configuration"""
        try:
            # Validate credential exists and belongs to user
            credential = await self.credential_crud.get_by_owner_and_id(
                owner_id, model_data.credential_id
            )
            if not credential:
                raise AppError(
                    message="Credential not found or does not belong to user",
                    status_code=404
                )

            # Check if model name already exists for this owner
            if await self.crud.check_name_exists(owner_id, model_data.name):
                raise AppError(
                    message=f"Model name '{model_data.name}' already exists",
                    status_code=400
                )

            # If setting as default, ensure no other default exists for this type
            if model_data.is_default:
                existing_default = await self.crud.get_default_model(owner_id, model_data.type)
                if existing_default:
                    # Unset existing default
                    await self.crud.set_default_model(owner_id, str(existing_default.id), model_data.type)

            # Create the model
            model = await self.crud.create_with_owner(owner_id, model_data)

            # If this is set as default, update it
            if model_data.is_default:
                await self.crud.set_default_model(owner_id, str(model.id), model_data.type)

            return self._to_response(model)

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                message=f"Failed to create model: {str(e)}",
                status_code=500
            )

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
            if model_type:
                models = await self.crud.get_by_type(owner_id, model_type)
                logger.debug(f"Models retrieved successfully: {models}")
            elif credential_id:
                models = await self.crud.get_by_credential(owner_id, credential_id)
                logger.debug(f"Models retrieved successfully: {models}")
            elif active_only:
                models = await self.crud.get_active_models(owner_id)
                logger.debug(f"Models retrieved successfully: {models}")
            else:
                models = await self.crud.get_by_owner(owner_id, skip, limit)
                logger.debug(f"Models retrieved successfully: {models}")
            # Apply additional filtering if needed
            if active_only:
                models = [m for m in models if m.is_active]

            # Apply pagination for filtered results
            total = len(models)
            if not model_type and not credential_id and not active_only:
                # Only apply skip/limit if we haven't already filtered
                models = models[skip:skip + limit] if limit > 0 else models[skip:]

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
        update_data: ModelUpdate
    ) -> Optional[ModelResponse]:
        """Update a model configuration"""
        try:
            # Get existing model
            model = await self.crud.get_by_owner_and_id(owner_id, model_id)
            if not model:
                return None

            # Check name uniqueness if name is being updated
            if update_data.name and update_data.name != model.name:
                if await self.crud.check_name_exists(owner_id, update_data.name, model_id):
                    raise AppError(
                        message=f"Model name '{update_data.name}' already exists",
                        status_code=400
                    )

            # Handle default model logic
            if update_data.is_default is True and not model.is_default:
                await self.crud.set_default_model(owner_id, model_id, model.type)
            elif update_data.is_default is False and model.is_default:
                # Allow unsetting default, but warn if no other default exists
                pass

            # Update the model
            updated_model = await self.crud.update(model, update_data)
            return self._to_response(updated_model)

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                message=f"Failed to update model: {str(e)}",
                status_code=500
            )

    async def delete_model(self, owner_id: str, model_id: str) -> bool:
        """Delete a model (soft delete)"""
        try:
            model = await self.crud.get_by_owner_and_id(owner_id, model_id)
            if not model:
                return False

            await self.crud.soft_delete(model)
            return True

        except Exception as e:
            raise AppError(
                message=f"Failed to delete model: {str(e)}",
                status_code=500
            )

    async def set_default_model(
        self,
        owner_id: str,
        model_id: str
    ) -> Optional[ModelResponse]:
        """Set a model as the default for its type"""
        try:
            model = await self.crud.get_by_owner_and_id(owner_id, model_id)
            if not model:
                return None

            success = await self.crud.set_default_model(owner_id, model_id, model.type)
            if not success:
                raise AppError(
                    message="Failed to set model as default",
                    status_code=500
                )

            # Refresh model data
            updated_model = await self.crud.get_by_owner_and_id(owner_id, model_id)
            return self._to_response(updated_model) if updated_model else None

        except AppError:
            raise
        except Exception as e:
            raise AppError(
                message=f"Failed to set default model: {str(e)}",
                status_code=500
            )

    async def get_default_model(
        self,
        owner_id: str,
        model_type: ModelType
    ) -> Optional[ModelResponse]:
        """Get the default model for a specific type"""
        try:
            model = await self.crud.get_default_model(owner_id, model_type)
            return self._to_response(model) if model else None

        except Exception as e:
            raise AppError(
                message=f"Failed to get default model: {str(e)}",
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
            is_default=model.is_default,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
