from typing import Optional, Dict, Any

from app.crud.model import ModelCRUD
from app.crud.credential import CredentialCRUD
from app.models.model import Model, ModelType
from app.schemas.model import ModelCreate, ModelResponse, ModelStats, ModelUpdateRequest
from app.core.exceptions import AppError
from app.utils.logging import get_logger
from app.services.credential_service import CredentialService
from langchain_openai import OpenAIEmbeddings
from openai import NotFoundError, UnprocessableEntityError, BadRequestError
logger = get_logger(__name__)

class ModelService:
    def __init__(self):
        self.crud = ModelCRUD()
        self.credential_crud = CredentialCRUD()
        self.credential_service = CredentialService()


    def _verify_and_get_embed_dimension(self, model: str, base_url, api_key) -> int:
        """Get the embedding dimension for a model"""
        try:
            embeddings = OpenAIEmbeddings(model=model, base_url=base_url, api_key=api_key)
            result = embeddings.embed_query("Check!")
            return len(result)
        except NotFoundError as e:
            logger.error(f"Model not found: {e}")
            raise AppError(message=f"{e.response.json()["error"]["message"]}", status_code=404)
        except UnprocessableEntityError as e:
            logger.error(f"Model is not supported: {e}")
            raise AppError(message=f"Model is not supported", status_code=400)
        except BadRequestError as e:
            logger.error(f"Model is not supported: {e}")
            raise AppError(message=f"{e.response.json()["error"]["message"]}", status_code=400)
        except Exception as e:
            logger.error(f"Model is not supported: {e}")
            raise AppError(message=f"Model is not supported", status_code=500)


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

            if model_data.type == ModelType.EMBEDDING:
              embed_dimension = self._verify_and_get_embed_dimension(model_data.model, credential.base_url, api_key)
              if embed_dimension:
                model_data.dimension = embed_dimension
              else:
                  return False

            # Create the model
            await self.crud.create_with_owner(owner_id, model_data)

            logger.info(f"Model created successfully for user {owner_id}")
            return True

        except AppError:
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
        if model.type == ModelType.EMBEDDING:
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
                updated_at=model.updated_at,
                dimension=model.dimension
            )
        else:
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
