from typing import Dict, Any, Optional
import asyncio
from app.utils.celery_client import embedding_client
from app.utils.logging import get_logger
from app.services.credential_service import CredentialService
from app.services.model_service import ModelService
from app.services.provider_service import ProviderService
from app.crud.task import TaskCRUD
from app.schemas.embedding import EmbeddingRequest, TextEmbeddingRequest
from app.crud.file import FileCRUD
from app.crud.user import UserCRUD
from app.crud.knowledge_store import knowledge_store_crud
logger = get_logger(__name__)


class EmbeddingService:
    """Service class for managing embedding tasks with external AI Tasks System"""
    def __init__(self):
        self.model_service = ModelService()
        self.provider_service = ProviderService()
        self.credential_service = CredentialService()
        self.file_crud = FileCRUD()
        self.user_crud = UserCRUD()

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
            user = await self.user_crud.get_by_id(id=user_id)
            if not user:
                raise ValueError(f"User with ID '{user_id}' not found")

            secret_key = getattr(user, "minio_secret_key", None) if user else None
            if not secret_key:
                raise ValueError("User MinIO secret key not found")

            file = await self.file_crud.get_by_id(id=embedding_data.file_id, owner_id=user_id)
            if not file:
                raise ValueError(f"File with ID '{embedding_data.file_id}' not found")

            # Get knowledge store if provided
            knowledge_store = None
            if embedding_data.knowledge_store_id:
                knowledge_store = await knowledge_store_crud.get_by_id(
                    id=embedding_data.knowledge_store_id,
                    owner_id=user_id
                )
                if not knowledge_store:
                    raise ValueError(f"Knowledge store with ID '{embedding_data.knowledge_store_id}' not found")

            # Get model configuration (required)
            model = await self.model_service.get_model(user_id, embedding_data.model_id)
            if not model:
                raise ValueError(f"Model with ID '{embedding_data.model_id}' not found")

            # Check if model is active
            if not model.is_active:
                raise ValueError(f"Model '{model.name}' is not active. Please activate the model or choose another one.")

            credential = await self.credential_service.get_credential(user_id, model.credential_id)
            if not credential:
                raise ValueError(f"Credential with ID '{model.credential_id}' not found")

            provider_obj = await self.provider_service.get_provider_by_id(credential.provider_id)
            if not provider_obj:
                raise ValueError(f"Provider with ID '{credential.provider_id}' not found")

            provider = provider_obj.provider
            model_id = model.model
            model_name = model.name
            credential_data = {
                "api_key": credential.api_key,
                "base_url": credential.base_url,
                "additional_headers": credential.additional_headers,
                "provider": provider_obj.provider,
                "secret_key": secret_key
            }


            # Create embedding task with knowledge store info
            task_kwargs = {
                "user_id": user_id,
                "object_name": file.file_path,
                "provider": provider,
                "model_id": model_id,
                "credential": credential_data,
                "file_id": embedding_data.file_id
            }

            if knowledge_store:
                task_kwargs["knowledge_store_id"] = embedding_data.knowledge_store_id
                task_kwargs["collection_name"] = knowledge_store.collection_name

            task_id = embedding_client.create_embedding_task(**task_kwargs)
            try:
                task_crud = TaskCRUD()
                task_data = {
                    "task_id": task_id,
                    "task_type": "embedding",
                    "user_id": user_id,
                    "file_id": embedding_data.file_id,
                    "provider": provider,
                    "model_id": model_id,
                    "status": "STARTED",
                    "metadata": {
                        "model_name": model_name,
                        "file_name": file.file_name
                    }
                }

                if knowledge_store:
                    task_data["knowledge_store_id"] = embedding_data.knowledge_store_id
                    task_data["metadata"]["knowledge_store_name"] = knowledge_store.name
                    task_data["metadata"]["collection_name"] = knowledge_store.collection_name

                await task_crud.create(task_data)
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

    async def create_text_embedding_task(
        self,
        user_id: str,
        text_data: TextEmbeddingRequest,
    ) -> Dict[str, Any]:
        """
        Create a text embedding task using model configuration from database

        Args:
            user_id: User identifier
            text_data: TextEmbeddingRequest containing text and optional model_id

        Returns:
            Dict containing task creation result
        """
        try:
            user = await self.user_crud.get_by_id(id=user_id)
            if not user:
                raise ValueError(f"User with ID '{user_id}' not found")

            # Get knowledge store if provided
            knowledge_store = None
            if text_data.knowledge_store_id:
                knowledge_store = await knowledge_store_crud.get_by_id(
                    id=text_data.knowledge_store_id,
                    owner_id=user_id
                )
                if not knowledge_store:
                    raise ValueError(f"Knowledge store with ID '{text_data.knowledge_store_id}' not found")

            # Get model configuration (required)
            model = await self.model_service.get_model(user_id, text_data.model_id)
            if not model:
                raise ValueError(f"Model with ID '{text_data.model_id}' not found")

            # Check if model is active
            if not model.is_active:
                raise ValueError(f"Model '{model.name}' is not active. Please activate the model or choose another one.")

            credential = await self.credential_service.get_credential(user_id, model.credential_id)
            if not credential:
                raise ValueError(f"Credential with ID '{model.credential_id}' not found")

            provider_obj = await self.provider_service.get_provider_by_id(credential.provider_id)
            if not provider_obj:
                raise ValueError(f"Provider with ID '{credential.provider_id}' not found")

            provider = provider_obj.provider
            model_id = model.model
            model_name = model.name
            credential_data = {
                "api_key": credential.api_key,
                "base_url": credential.base_url,
                "additional_headers": credential.additional_headers,
                "provider": provider_obj.provider,
            }

            # Create text embedding task
            task_kwargs = {
                "user_id": user_id,
                "text": text_data.text,
                "provider": provider,
                "model_id": model_id,
                "credential": credential_data
            }

            if knowledge_store:
                task_kwargs["knowledge_store_id"] = text_data.knowledge_store_id
                task_kwargs["collection_name"] = knowledge_store.collection_name

            task_id = embedding_client.create_text_embedding_task(**task_kwargs)

            try:
                task_crud = TaskCRUD()
                task_data = {
                    "task_id": task_id,
                    "task_type": "text_embedding",
                    "user_id": user_id,
                    "file_id": None,
                    "provider": provider,
                    "model_id": model_id,
                    "status": "STARTED",
                    "metadata": {
                        "model_name": model_name,
                        "text_length": len(text_data.text)
                    }
                }

                if knowledge_store:
                    task_data["knowledge_store_id"] = text_data.knowledge_store_id
                    task_data["metadata"]["knowledge_store_name"] = knowledge_store.name
                    task_data["metadata"]["collection_name"] = knowledge_store.collection_name

                await task_crud.create(task_data)
            except Exception as e:
                logger.warning(f"Failed to persist text embedding task document: {e}")

            return {
                "success": True,
                "task_id": task_id,
                "message": "Text embedding task created",
                "metadata": {
                    "user_id": user_id,
                    "model_name": model_name,
                    "model_identifier": model_id,
                    "provider": provider,
                    "text_length": len(text_data.text),
                    "knowledge_store_id": text_data.knowledge_store_id
                }
            }

        except Exception as e:
            logger.error(f"Error creating text embedding task: {e}")
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

            # Initialize credential service for AI providers
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
    async def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        Async version to get enhanced task status with MongoDB metadata
        """
        try:
            # Get real-time status from Celery
            celery_status = embedding_client.get_task_status(task_id)

            # Get task metadata from MongoDB
            from app.crud.task import TaskCRUD
            task_crud = TaskCRUD()

            task_doc = await task_crud.get_by_task_id(task_id)

            if task_doc:
                enhanced_status = {
                    "task_id": task_id,
                    "status": celery_status.get("status"),
                    "ready": celery_status.get("ready"),
                    "successful": celery_status.get("successful"),
                    "failed": celery_status.get("failed"),
                    "result": celery_status.get("result"),
                    "error": celery_status.get("error"),
                    "meta": celery_status.get("meta"),

                    "task_type": task_doc.task_type,
                    "user_id": task_doc.user_id,
                    "file_id": task_doc.file_id,
                    "knowledge_store_id": task_doc.knowledge_store_id,
                    "provider": task_doc.provider,
                    "model_id": task_doc.model_id,
                    "created_at": task_doc.created_at.isoformat() if task_doc.created_at else None,
                    "updated_at": task_doc.updated_at.isoformat() if task_doc.updated_at else None,
                }

                # ✨ Add enhanced metadata from MongoDB
                if task_doc.metadata:
                    if isinstance(enhanced_status["meta"], dict):
                        enhanced_status["meta"].update(task_doc.metadata)
                    elif isinstance(enhanced_status["meta"], str):
                        # If meta is string, create dict and add MongoDB metadata
                        enhanced_status["meta"] = {
                            "status_message": enhanced_status["meta"],
                            **task_doc.metadata
                        }
                    else:
                        enhanced_status["meta"] = task_doc.metadata

                # ✨ Sync status to MongoDB if different
                celery_status_val = celery_status.get("status")
                db_status = task_doc.status

                if celery_status_val != db_status:
                    update_data = {"status": celery_status_val}

                    # Update metadata with result if task completed
                    if celery_status_val == "SUCCESS" and celery_status.get("result"):
                        if not task_doc.metadata:
                            task_doc.metadata = {}
                        update_data["metadata"] = {**task_doc.metadata, "result": celery_status.get("result")}

                    # Update error if task failed
                    if celery_status_val in ["FAILURE", "ERROR"] and celery_status.get("error"):
                        update_data["error"] = celery_status.get("error")

                    await task_crud.update(task_doc, update_data)
                    logger.info(f"🔄 Synced task {task_id} status from {db_status} to {celery_status_val} in MongoDB")

                return enhanced_status
            else:
                # Task not found in MongoDB, return Celery data only
                logger.warning(f"⚠️ Task {task_id} not found in MongoDB, returning Celery data only")
                return celery_status

        except Exception as e:
            logger.error(f"❌ Error getting enhanced status for {task_id}: {e}")
            return embedding_client.get_task_status(task_id)



    @staticmethod
    async def cancel_task(task_id: str) -> Dict[str, Any]:
        """
        Async version to cancel a running embedding task and update MongoDB
        """
        try:
            logger.info(f"Cancelling embedding task: {task_id}")

            # Cancel in Celery
            celery_result = embedding_client.cancel_task(task_id)

            # Update MongoDB status
            from app.crud.task import TaskCRUD
            task_crud = TaskCRUD()

            task_doc = await task_crud.get_by_task_id(task_id)
            if task_doc:
                # Map Celery status to MongoDB status
                mongodb_status = "REVOKED" if celery_result.get("status") == "CANCELLED" else celery_result.get("status")

                await task_crud.update(task_doc, {
                    "status": mongodb_status,
                    "error": celery_result.get("error")
                })
                logger.info(f"🔄 Updated task {task_id} status to {mongodb_status} in MongoDB")
            else:
                logger.warning(f"⚠️ Task {task_id} not found in MongoDB during cancellation")

            return celery_result

        except Exception as e:
            logger.error(f"❌ Error cancelling embedding task {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "error": f"Failed to cancel task: {str(e)}"
            }

