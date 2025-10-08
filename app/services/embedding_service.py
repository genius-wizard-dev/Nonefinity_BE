"""
Service for creating and managing vector embedding tasks with external AI Tasks System
"""

from typing import Dict, Any, List, Optional
import asyncio

from app.utils.celery_client import embedding_client
from app.utils.logging import get_logger
from app.services.credential_service import CredentialService
from app.services.model_service import ModelService
from app.services.provider_service import ProviderService
from app.crud.task import TaskCRUD
from app.schemas.embedding import EmbeddingRequest
logger = get_logger(__name__)


class EmbeddingService:
    """Service class for managing embedding tasks with external AI Tasks System"""
    def __init__(self):
        self.model_service = ModelService()
        self.provider_service = ProviderService()
        self.credential_service = CredentialService()


    async def create_embedding_task(
        self,
        user_id: str,
        embedding_data: EmbeddingRequest,
    ) -> Dict[str, Any]:
        """
        Create an embedding task using model configuration from database

        Args:
            user_id: User identifier
            embedding_data: EmbeddingRequest containing file_id and optional model_id

        Returns:
            Dict containing task creation result
        """
        try:
            # Initialize default values
            model_id = "sentence-transformers/all-MiniLM-L6-v2"
            provider = "local"
            credential_data = {}
            model_name = "Default OSS"

            # If model_id is provided, get model and credential information
            if embedding_data.model_id:

                model = await self.model_service.get_model(user_id, embedding_data.model_id)
                if not model:
                    raise ValueError(f"Model with ID '{embedding_data.model_id}' not found")
                model_id = model.model
                credential = await self.credential_service.get_credential(user_id, model.credential_id)
                if not credential:
                    raise ValueError(f"Credential with ID '{model.credential_id}' not found")

                provider_obj = await self.provider_service.get_provider_by_id(credential.provider_id)
                if not provider_obj:
                    raise ValueError(f"Provider with ID '{credential.provider_id}' not found")

                # Set provider and credential data
                provider = provider_obj.provider
                model_name = model.name
                credential_data = {
                    "api_key": credential.api_key,
                    "base_url": credential.base_url,
                    "additional_headers": credential.additional_headers,
                    "provider": provider_obj.provider
                }

            # Always use file embedding task (no text support)
            task_id = embedding_client.create_embedding_task(
                user_id=user_id,
                file_id=embedding_data.file_id,
                provider=provider,
                model_id=model_id,
                credential=credential_data
            )

            logger.info(f"Embedding task created: {task_id} with provider: {provider}, model: {model_id}")

            # Persist task to MongoDB for tracking
            try:
                task_crud = TaskCRUD()
                await task_crud.create({
                    "task_id": task_id,
                    "task_type": "embedding",
                    "user_id": user_id,
                    "file_id": embedding_data.file_id,
                    "provider": provider,
                    "model_id": model_id,
                    "status": "STARTED",
                    "metadata": {
                        "model_name": model_name
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to persist embedding task document: {e}")

            return {
                "success": True,
                "task_id": task_id,
                "message": "Embedding task created",
                "metadata": {
                    "user_id": user_id,
                    "model_name": model_name,
                    "model_identifier": model_id,
                    "provider": provider,
                    "file_id": embedding_data.file_id,
                    "chunks_count": 0
                }
            }

        except Exception as e:
            logger.error(f"Error creating embedding task: {e}")
            return {
                "success": False,
                "error": f"Service error: {str(e)}",
                "task_id": None
            }

    @staticmethod
    async def create_search_task(
        user_id: str,
        credential_id: Optional[str],
        query_text: str,
        provider: str = "huggingface",
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
        file_id: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Create a similarity search task

        Args:
            user_id: User identifier
            credential_id: Credential identifier for API key
            query_text: Text to search for
            provider: Embedding provider
            model_id: Model identifier
            file_id: Optional filter by file
            limit: Number of results to return

        Returns:
            Dict containing task creation result
        """
        try:
            logger.info(
                f"Creating search task for user {user_id}, credential {credential_id}")

            # For local/HuggingFace sentence-transformers used locally, credential is optional
            credential_data = {}
            if provider.lower() not in ("huggingface", "hf", "local"):
                # Initialize credential service for non-local providers
                credential_service = CredentialService()
                db_credential = await credential_service.crud.get_by_owner_and_id(user_id, credential_id)
                if not db_credential:
                    return {
                        "success": False,
                        "error": "Credential not found",
                        "task_id": None
                    }
                decrypted_api_key = credential_service._decrypt_api_key(
                    db_credential.api_key)
                credential_data = {
                    "api_key": decrypted_api_key,
                    "base_url": db_credential.base_url
                }

            # Create search task via AI Tasks Client
            task_id = embedding_client.search_embeddings(
                query_text=query_text,
                provider=provider,
                model_id=model_id,
                credential=credential_data,
                user_id=user_id,
                file_id=file_id,
                limit=limit
            )

            logger.info(f"Search task created successfully: {task_id}")
            # Persist search task
            try:
                task_crud = TaskCRUD()
                await task_crud.create({
                    "task_id": task_id,
                    "task_type": "search",
                    "user_id": user_id,
                    "file_id": file_id,
                    "provider": provider,
                    "model_id": model_id,
                    "status": "STARTED",
                    "metadata": {"limit": limit, "query_length": len(query_text)}
                })
            except Exception:
                logger.warning("Failed to persist search task document")
            return {
                "success": True,
                "task_id": task_id,
                "message": "Search task created successfully",
                "metadata": {
                    "user_id": user_id,
                    "query_length": len(query_text),
                    "provider": provider,
                    "model_id": model_id,
                    "limit": limit
                }
            }

        except Exception as e:
            logger.error(f"Error creating search task: {e}")
            return {
                "success": False,
                "error": f"Service error: {str(e)}",
                "task_id": None
            }

    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        Get the status of an embedding task by task ID

        Args:
            task_id: Task identifier

        Returns:
            Dict containing task status and information
        """

        try:
            logger.debug(f"Getting embedding task status: {task_id}")
            status = embedding_client.get_task_status(task_id)
            # Status persistence handled by Celery signals now
            return status

        except Exception as e:
            logger.error(
                f"Error getting embedding task status for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "ready": False,
                "successful": False,
                "failed": True,
                "result": None,
                "error": f"Service error: {str(e)}",
                "meta": None
            }

    @staticmethod
    def get_task_result(task_id: str) -> Dict[str, Any]:
        """
        Get the result of a completed embedding task

        Args:
            task_id: Task identifier

        Returns:
            Dict containing task result or error information
        """

        try:
            logger.debug(f"Getting embedding task result: {task_id}")
            result = embedding_client.get_task_result(task_id)
            # Completion persistence handled by Celery signals now
            return result

        except Exception as e:
            logger.error(
                f"Error getting embedding task result for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "ready": False,
                "successful": False,
                "failed": True,
                "result": None,
                "error": f"Service error: {str(e)}"
            }

    @staticmethod
    def cancel_task(task_id: str) -> Dict[str, Any]:
        """
        Cancel a running embedding task

        Args:
            task_id: Task identifier

        Returns:
            Dict containing cancellation status
        """

        try:
            logger.info(f"Cancelling embedding task: {task_id}")
            res = embedding_client.cancel_task(task_id)
            # Persist cancel
            try:
                task_crud = TaskCRUD()
                doc = asyncio.get_event_loop().run_until_complete(task_crud.get_by_task_id(task_id))  # type: ignore
                if doc:
                    asyncio.get_event_loop().run_until_complete(task_crud.update(doc, {"status": res.get("status")}))  # type: ignore
            except Exception:
                pass
            return res

        except Exception as e:
            logger.error(f"Error cancelling embedding task {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "error": f"Service error: {str(e)}"
            }

    # @staticmethod
    # def get_active_tasks() -> Dict[str, Any]:
    #     """
    #     Get information about currently active embedding tasks

    #     Returns:
    #         Dict containing active task information
    #     """

    #     try:
    #         logger.debug("Getting active embedding tasks information")
    #         return embedding_client.get_active_tasks()

    #     except Exception as e:
    #         logger.error(f"Error getting active embedding tasks: {e}")
    #         return {
    #             "active_tasks": {},
    #             "total_active": 0,
    #             "error": f"Service error: {str(e)}"
    #         }

    # @staticmethod
    # def get_active_tasks() -> Dict[str, Any]:
    #     """
    #     Get information about currently active embedding tasks

    #     Returns:
    #         Dict containing active task information
    #     """

    #     try:
    #         logger.debug("Getting active embedding tasks information")
    #         return embedding_client.get_active_tasks()

    #     except Exception as e:
    #         logger.error(f"Error getting active embedding tasks: {e}")
    #         return {
    #             "active_tasks": {},
    #             "total_active": 0,
    #             "error": f"Service error: {str(e)}"
    #         }
