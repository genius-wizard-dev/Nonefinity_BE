"""
Celery client utility for connecting to external AI Tasks System
"""

from typing import Dict, Any, Optional
from celery import Celery
from celery.result import AsyncResult

from app.configs.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AITasksClient:
    """Client for interacting with external AI Tasks System"""

    def __init__(self, app_name: str = "ai_tasks_client"):
        """
        Initialize AI tasks client

        Args:
            app_name: Name of the client application
        """
        self.app_name = app_name
        self._celery_app = None
        self._initialize_client()

        logger.info(f"Initialized AI Tasks Client: {app_name}")

    def _initialize_client(self):
        """Initialize the Celery client connection"""
        try:
            # Create Celery client
            self._celery_app = Celery(
                self.app_name,
                broker=settings.get_broker_url,
                backend=settings.get_result_backend,
            )

            # Configure client to match external system
            self._celery_app.conf.update(
                task_serializer=settings.CELERY_TASK_SERIALIZER,
                accept_content=settings.CELERY_ACCEPT_CONTENT,
                result_serializer=settings.CELERY_RESULT_SERIALIZER,
                timezone=settings.CELERY_TIMEZONE,
                enable_utc=settings.CELERY_ENABLE_UTC,
                result_expires=3600,  # Results expire after 1 hour
                task_ignore_result=False,
                task_track_started=True,
            )

        except Exception as e:
            logger.error(f"Failed to initialize AI Tasks client: {e}")
            raise

    # Avoid async DB calls in this sync client; persistence is handled at service layer

    @property
    def celery_app(self) -> Celery:
        """Get the Celery app instance (lazy loading)"""
        if self._celery_app is None:
            self._initialize_client()
        return self._celery_app

    def create_embedding_task(
        self,
        user_id: str,
        object_name: str,
        provider: str = "huggingface",
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
        credential: Dict[str, Any] = None,
        file_id: str = None,
        knowledge_store_id: str = None,
        collection_name: str = None,
    ) -> str:
        """
        Create an embedding task

        Args:
            user_id: User identifier
            object_name: Object name in MinIO storage
            provider: Embedding provider (openai, huggingface)
            model_id: Model identifier
            credential: Dictionary containing API keys
            file_id: File identifier
            knowledge_store_id: Knowledge store identifier
            collection_name: Qdrant collection name

        Returns:
            Task ID
        """
        try:
            logger.info(
                f"Creating embedding task for user {user_id}, provider {provider}, "
                f"model {model_id}, object: {object_name}"
            )

            # Send task to queue
            result = self.celery_app.send_task(
                'tasks.embedding.run_embedding',
                kwargs={
                    'user_id': user_id,
                    'object_name': object_name,
                    'provider': provider,
                    'model_id': model_id,
                    'credential': credential or {},
                    'file_id': file_id,
                    'knowledge_store_id': knowledge_store_id,
                    'collection_name': collection_name,
                },
                queue='embeddings'
            )

            return result.id

        except Exception as e:
            logger.error(f"Error creating embedding task: {e}")
            raise

    def create_text_embedding_task(
        self,
        user_id: str,
        text: str,
        provider: str = "huggingface",
        model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
        credential: Dict[str, Any] = None,
        knowledge_store_id: str = None,
        collection_name: str = None,
    ) -> str:
        """
        Create a text embedding task for direct text input

        Args:
            user_id: User identifier
            text: Text to embed directly
            provider: Embedding provider (openai, huggingface, google)
            model_id: Model identifier
            credential: Dictionary containing API keys
            knowledge_store_id: Knowledge store identifier
            collection_name: Qdrant collection name

        Returns:
            Task ID
        """
        try:
            logger.info(
                f"Creating text embedding task for user {user_id}, provider {provider}, "
                f"model {model_id}, text length: {len(text)}"
            )

            # Send task to queue
            result = self.celery_app.send_task(
                'tasks.embedding.run_text_embedding',
                kwargs={
                    'user_id': user_id,
                    'text': text,
                    'provider': provider,
                    'model_id': model_id,
                    'credential': credential or {},
                    'knowledge_store_id': knowledge_store_id,
                    'collection_name': collection_name,
                },
                queue='embeddings'
            )

            logger.info(f"Text embedding task created with ID: {result.id}")
            return result.id

        except Exception as e:
            logger.error(f"Error creating text embedding task: {e}")
            raise

    def search_embeddings(
        self,
        query_text: str,
        provider: str,
        model_id: str,
        credential: Dict[str, Any],
        user_id: str = None,
        file_id: str = None,
        limit: int = 5
    ) -> str:
        """
        Search for similar embeddings

        Args:
            query_text: Text to search for
            provider: Embedding provider
            model_id: Model identifier
            credential: Dictionary containing API keys
            user_id: Optional filter by user
            file_id: Optional filter by file
            limit: Number of results to return

        Returns:
            Task ID
        """
        try:
            logger.info(
                f"Creating search task for query length {len(query_text)}, "
                f"provider {provider}, model {model_id}, limit {limit}"
            )

            result = self.celery_app.send_task(
                'ai.embeddings.tasks.search_similar',
                kwargs={
                    'query_text': query_text,
                    'provider': provider,
                    'model_id': model_id,
                    'credential': credential,
                    'user_id': user_id,
                    'file_id': file_id,
                    'limit': limit
                },
                queue='embeddings'
            )

            logger.info(f"Search task created with ID: {result.id}")
            return result.id

        except Exception as e:
            logger.error(f"Error creating search task: {e}")
            raise

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task by task ID

        Args:
            task_id: Task identifier

        Returns:
            Dict containing task status and information
        """

        try:
            result = AsyncResult(task_id, app=self.celery_app)

            response = {
                "task_id": task_id,
                "status": result.state,
                "ready": result.ready(),
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
                "result": None,
                "error": None,
                "meta": None
            }

            # Get additional information based on state
            if result.state == 'PENDING':
                response["meta"] = "Task is waiting to be processed"
            elif result.state == 'STARTED':
                response["meta"] = "Task has started processing"
            elif result.state == 'PROGRESS':
                response["meta"] = result.info
            elif result.state == 'SUCCESS':
                response["result"] = result.get()
                response["meta"] = "Task completed successfully"
            elif result.state == 'FAILURE':
                response["error"] = str(result.info)
                response["meta"] = "Task failed"
            elif result.state == 'RETRY':
                response["meta"] = f"Task is being retried: {result.info}"
            elif result.state == 'REVOKED':
                response["meta"] = "Task was revoked"
            else:
                response["meta"] = f"Unknown task state: {result.state}"

            return response

        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "ready": False,
                "successful": False,
                "failed": True,
                "result": None,
                "error": f"Client error: {str(e)}",
                "meta": None
            }

    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """
        Get the result of a completed task

        Args:
            task_id: Task identifier

        Returns:
            Dict containing task result or error information
        """

        try:
            result = AsyncResult(task_id, app=self.celery_app)

            response = {
                "task_id": task_id,
                "status": result.state,
                "ready": result.ready(),
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
                "result": None,
                "error": None
            }

            if result.state == 'SUCCESS':
                response["result"] = result.get()
            elif result.state == 'FAILURE':
                response["error"] = str(result.info)
            elif result.state in ['PENDING', 'STARTED', 'PROGRESS', 'RETRY']:
                response["error"] = f"Task not yet completed. Current state: {result.state}"

            return response

        except Exception as e:
            logger.error(f"Error getting task result for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "ready": False,
                "successful": False,
                "failed": True,
                "result": None,
                "error": f"Client error: {str(e)}"
            }

    def wait_for_result(self, task_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Wait for a task to complete and return the result

        Args:
            task_id: Task identifier
            timeout: Timeout in seconds (None = wait forever)

        Returns:
            Dict containing final result
        """

        try:
            logger.info(
                f"Waiting for task {task_id} to complete (timeout: {timeout}s)")

            result = AsyncResult(task_id, app=self.celery_app)

            # Wait for completion
            final_result = result.get(timeout=timeout)

            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "ready": True,
                "successful": True,
                "failed": False,
                "result": final_result,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error waiting for task {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "ready": True,
                "successful": False,
                "failed": True,
                "result": None,
                "error": str(e)
            }

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel a running task

        Args:
            task_id: Task identifier

        Returns:
            Dict containing cancellation status
        """

        try:
            logger.info(f"Cancelling task: {task_id}")

            result = AsyncResult(task_id, app=self.celery_app)
            result.revoke(terminate=True)

            return {
                "task_id": task_id,
                "status": "CANCELLED",
                "message": "Task has been cancelled"
            }

        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "ERROR",
                "error": f"Failed to cancel task: {str(e)}"
            }

    # def get_active_tasks(self) -> Dict[str, Any]:
    #     """
    #     Get information about currently active tasks

    #     Returns:
    #         Dict containing active task information
    #     """

    #     try:
    #         logger.debug("Getting active tasks information")

    #         # Get active tasks from Celery
    #         inspect = self.celery_app.control.inspect()
    #         active_tasks = inspect.active()

    #         if not active_tasks:
    #             return {
    #                 "active_tasks": {},
    #                 "total_active": 0,
    #                 "message": "No active tasks found"
    #             }

    #         total_active = sum(len(tasks) for tasks in active_tasks.values())

    #         return {
    #             "active_tasks": active_tasks,
    #             "total_active": total_active,
    #             "workers": list(active_tasks.keys())
    #         }

    #     except Exception as e:
    #         logger.error(f"Error getting active tasks: {e}")
    #         return {
    #             "active_tasks": {},
    #             "total_active": 0,
    #             "error": str(e)
    #         }


# Singleton instances for common use cases
embedding_client = AITasksClient("embedding_client")
default_client = AITasksClient("default_client")
