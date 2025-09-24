"""
Service for creating and managing vector embedding tasks with external AI Tasks System
"""

from typing import Dict, Any, List, Optional

from app.utils.celery_client import embedding_client
from app.utils.logging import get_logger
from app.services.credential_service import credential_service
from app.services.model_service import ModelService
from app.services.provider_service import ProviderService

logger = get_logger(__name__)


class EmbeddingService:
    """Service class for managing embedding tasks with external AI Tasks System"""

    @staticmethod
    async def create_embedding_task(
        user_id: str,
        model_id: str,
        file_id: str,
    ) -> Dict[str, Any]:
        """
        Create an embedding task using model configuration from database

        Args:
            user_id: User identifier
            model_id: AI model identifier from database
            file_id: File identifier to process
            chunks: Optional list of text chunks to embed

        Returns:
            Dict containing task creation result
        """
        try:
            logger.info(f"Creating embedding task for user {user_id}, model {model_id}, file {file_id}")

            # Initialize services
            model_service = ModelService()

            # Get model configuration
            db_model = await model_service.crud.get_by_owner_and_id(user_id, model_id)
            if not db_model:
                return {
                    "success": False,
                    "error": "Model not found or does not belong to user",
                    "task_id": None
                }

            # Validate model type
            if db_model.type.value != "embedding":
                return {
                    "success": False,
                    "error": "Model is not an embedding model",
                    "task_id": None
                }

            # Get and decrypt credential
            db_credential = await credential_service.crud.get_by_owner_and_id(user_id, db_model.credential_id)
            if not db_credential:
                return {
                    "success": False,
                    "error": "Credential not found",
                    "task_id": None
                }

            # Get provider information
            provider_info = await ProviderService.get_provider_by_id(db_credential.provider_id)
            if not provider_info:
                return {
                    "success": False,
                    "error": "Provider not found",
                    "task_id": None
                }

            # Decrypt the API key
            decrypted_api_key = credential_service._decrypt_api_key(db_credential.api_key)

            # Prepare credential for external system
            credential_data = {
                "api_key": decrypted_api_key,
                "base_url": db_credential.base_url or provider_info.base_url
            }

            # Create task via AI Tasks Client
            task_id = embedding_client.create_embedding_task(
                user_id=user_id,
                file_id=file_id,
                provider=provider_info.provider,
                model_id=db_model.model,
                credential=credential_data
            )

            logger.info(f"Embedding task created successfully: {task_id}")
            return {
                "success": True,
                "task_id": task_id,
                "message": "Embedding task created successfully",
                "metadata": {
                    "user_id": user_id,
                    "model_name": db_model.name,
                    "model_identifier": db_model.model,
                    "provider": provider_info.provider,
                    "file_id": file_id,
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
        credential_id: str,
        query_text: str,
        provider: str = "openai",
        model_id: str = "text-embedding-ada-002",
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
            logger.info(f"Creating search task for user {user_id}, credential {credential_id}")

            # Get and decrypt credential
            db_credential = await credential_service.crud.get_by_owner_and_id(user_id, credential_id)
            if not db_credential:
                return {
                    "success": False,
                    "error": "Credential not found",
                    "task_id": None
                }

            # Decrypt the API key
            decrypted_api_key = credential_service._decrypt_api_key(db_credential.api_key)

            # Prepare credential for external system
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
            return embedding_client.get_task_status(task_id)

        except Exception as e:
            logger.error(f"Error getting embedding task status for {task_id}: {e}")
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
            return embedding_client.get_task_result(task_id)

        except Exception as e:
            logger.error(f"Error getting embedding task result for {task_id}: {e}")
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
            return embedding_client.cancel_task(task_id)

        except Exception as e:
            logger.error(f"Error cancelling embedding task {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "error": f"Service error: {str(e)}"
            }

    @staticmethod
    def get_active_tasks() -> Dict[str, Any]:
        """
        Get information about currently active embedding tasks

        Returns:
            Dict containing active task information
        """

        try:
            logger.debug("Getting active embedding tasks information")
            return embedding_client.get_active_tasks()

        except Exception as e:
            logger.error(f"Error getting active embedding tasks: {e}")
            return {
                "active_tasks": {},
                "total_active": 0,
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
