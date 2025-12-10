"""
Celery client utility for connecting to external AI Tasks System.

This client is designed to be decoupled from the Celery worker,
allowing the backend API to send tasks to a separate Celery server.
"""

from typing import Dict, Any, Optional
from celery import Celery
from celery.result import AsyncResult

from app.configs.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Task Names - Must match the names registered in the worker
# =============================================================================
class TaskNames:
    """Task name constants - keep in sync with worker task registrations"""
    # Embedding tasks (queue: embeddings)
    EMBEDDING_RUN = "tasks.embedding.run_embedding"
    EMBEDDING_TEXT = "tasks.embedding.run_text_embedding"
    EMBEDDING_SEARCH = "tasks.embedding.search_similar"

    # Chat tasks (queue: chats)
    CHAT_EXPORT_HISTORY = "tasks.chat.export_history"


# =============================================================================
# Queue Names
# =============================================================================
class QueueNames:
    """Queue name constants"""
    EMBEDDINGS = "embeddings"
    CHATS = "chats"


# =============================================================================
# Celery Client
# =============================================================================
class CeleryTaskClient:
    """
    Client for sending tasks to Celery workers.

    Designed to work with a remote Celery server - only needs Redis connection,
    does not need to import any task modules.
    """

    def __init__(self, app_name: str = "celery_client"):
        self.app_name = app_name
        self._celery_app: Optional[Celery] = None
        self._initialize_client()
        logger.info(f"Initialized Celery Client: {app_name}")

    def _initialize_client(self):
        """Initialize the Celery client connection"""
        try:
            self._celery_app = Celery(
                self.app_name,
                broker=settings.get_broker_url,
                backend=settings.get_result_backend,
            )

            self._celery_app.conf.update(
                task_serializer=settings.CELERY_TASK_SERIALIZER,
                accept_content=settings.CELERY_ACCEPT_CONTENT,
                result_serializer=settings.CELERY_RESULT_SERIALIZER,
                timezone=settings.CELERY_TIMEZONE,
                enable_utc=settings.CELERY_ENABLE_UTC,
                result_expires=3600,
                task_ignore_result=False,
                task_track_started=True,
            )

        except Exception as e:
            logger.error(f"Failed to initialize Celery client: {e}")
            raise

    @property
    def celery_app(self) -> Celery:
        """Get the Celery app instance"""
        if self._celery_app is None:
            self._initialize_client()
        return self._celery_app

    # =========================================================================
    # Generic Task Methods
    # =========================================================================
    def send_task(
        self,
        task_name: str,
        queue: str,
        kwargs: Dict[str, Any] = None,
        args: tuple = None,
    ) -> str:
        """
        Send a task to the Celery worker.

        Args:
            task_name: The registered task name
            queue: Target queue name
            kwargs: Task keyword arguments
            args: Task positional arguments

        Returns:
            Task ID
        """
        try:
            result = self.celery_app.send_task(
                task_name,
                args=args or (),
                kwargs=kwargs or {},
                queue=queue
            )
            logger.info(f"Task sent: {task_name} -> {queue} (ID: {result.id})")
            return result.id
        except Exception as e:
            logger.error(f"Error sending task {task_name}: {e}")
            raise

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task"""
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
        """Get the result of a completed task"""
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
        """Wait for a task to complete and return the result"""
        try:
            logger.info(f"Waiting for task {task_id} (timeout: {timeout}s)")
            result = AsyncResult(task_id, app=self.celery_app)
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
        """Cancel a running task"""
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

    # =========================================================================
    # Embedding Tasks
    # =========================================================================
    def create_embedding_task(
        self,
        user_id: str,
        object_name: str,
        provider: str,
        model_id: str,
        credential: Dict[str, Any],
        file_id: str = None,
        knowledge_store_id: str = None,
        collection_name: str = None,
    ) -> str:
        """Create a file embedding task"""
        logger.info(f"Creating embedding task: user={user_id}, object={object_name}")

        return self.send_task(
            task_name=TaskNames.EMBEDDING_RUN,
            queue=QueueNames.EMBEDDINGS,
            kwargs={
                'user_id': user_id,
                'object_name': object_name,
                'provider': provider,
                'model_id': model_id,
                'credential': credential or {},
                'file_id': file_id,
                'knowledge_store_id': knowledge_store_id,
                'collection_name': collection_name,
            }
        )

    def create_text_embedding_task(
        self,
        user_id: str,
        text: str,
        provider: str,
        model_id: str,
        credential: Dict[str, Any],
        knowledge_store_id: str = None,
        collection_name: str = None,
    ) -> str:
        """Create a text embedding task"""
        logger.info(f"Creating text embedding task: user={user_id}, text_len={len(text)}")

        return self.send_task(
            task_name=TaskNames.EMBEDDING_TEXT,
            queue=QueueNames.EMBEDDINGS,
            kwargs={
                'user_id': user_id,
                'text': text,
                'provider': provider,
                'model_id': model_id,
                'credential': credential or {},
                'knowledge_store_id': knowledge_store_id,
                'collection_name': collection_name,
            }
        )

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
        """Create a similarity search task"""
        logger.info(f"Creating search task: query_len={len(query_text)}")

        return self.send_task(
            task_name=TaskNames.EMBEDDING_SEARCH,
            queue=QueueNames.EMBEDDINGS,
            kwargs={
                'query_text': query_text,
                'provider': provider,
                'model_id': model_id,
                'credential': credential,
                'user_id': user_id,
                'file_id': file_id,
                'limit': limit
            }
        )

    # =========================================================================
    # Chat Tasks
    # =========================================================================
    def export_chat_history(
        self,
        task_id: str,
        config_id: str,
        owner_id: str,
        format: str = "json"
    ) -> str:
        """
        Create a chat history export task.

        Args:
            task_id: Task ID for tracking (created by service layer)
            config_id: Chat config ID to export
            owner_id: Owner user ID
            format: Export format ('json' or 'csv')

        Returns:
            Celery task ID
        """
        logger.info(f"Creating chat export task: config={config_id}, format={format}")

        return self.send_task(
            task_name=TaskNames.CHAT_EXPORT_HISTORY,
            queue=QueueNames.CHATS,
            kwargs={
                'task_id': task_id,
                'config_id': config_id,
                'owner_id': owner_id,
                'format': format
            }
        )


# =============================================================================
# Singleton Instances
# =============================================================================
# Main client instance - use this for all task operations
task_client = CeleryTaskClient("nonefinity_client")

# Backward compatibility aliases
embedding_client = task_client
default_client = task_client
