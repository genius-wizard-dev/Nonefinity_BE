"""
Celery client utility for connecting to external task systems
"""

from typing import Dict, Any, Optional
from celery import Celery
from celery.result import AsyncResult

from app.configs.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CeleryClientManager:
    """Manager for Celery client connections to external systems"""

    _clients: Dict[str, Celery] = {}

    @classmethod
    def get_client(cls, client_name: str = "default") -> Celery:
        """
        Get or create a Celery client instance

        Args:
            client_name: Name of the client (for multiple external systems)

        Returns:
            Celery client instance
        """

        if client_name not in cls._clients:
            cls._clients[client_name] = cls._create_client(client_name)
            logger.info(f"Created Celery client: {client_name}")

        return cls._clients[client_name]

    @classmethod
    def _create_client(cls, client_name: str) -> Celery:
        """
        Create a new Celery client instance

        Args:
            client_name: Name of the client

        Returns:
            Configured Celery client
        """

        # Create Celery client
        celery_client = Celery(
            f"{client_name}_client",
            broker=settings.get_broker_url,
            backend=settings.get_result_backend,
        )

        # Configure client to match external system
        celery_client.conf.update(
            task_serializer=settings.CELERY_TASK_SERIALIZER,
            accept_content=settings.CELERY_ACCEPT_CONTENT,
            result_serializer=settings.CELERY_RESULT_SERIALIZER,
            timezone=settings.CELERY_TIMEZONE,
            enable_utc=settings.CELERY_ENABLE_UTC,
            result_expires=3600,  # Results expire after 1 hour
            task_ignore_result=False,
            task_track_started=True,
        )

        logger.debug(f"Configured Celery client: {client_name}")
        return celery_client

    @classmethod
    def close_all_clients(cls):
        """Close all Celery client connections"""
        for client_name, client in cls._clients.items():
            try:
                client.close()
                logger.info(f"Closed Celery client: {client_name}")
            except Exception as e:
                logger.error(f"Error closing Celery client {client_name}: {e}")

        cls._clients.clear()


class TaskResultClient:
    """
    Generic client for getting task results from external Celery systems
    """

    def __init__(self, client_name: str = "default"):
        """
        Initialize task result client

        Args:
            client_name: Name of the Celery client to use
        """
        self.client_name = client_name
        self._celery_client: Optional[Celery] = None

    @property
    def celery_client(self) -> Celery:
        """Get the Celery client instance (lazy loading)"""
        if self._celery_client is None:
            self._celery_client = CeleryClientManager.get_client(self.client_name)
        return self._celery_client

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of a task by task ID

        Args:
            task_id: Task identifier

        Returns:
            Dict containing task status and information
        """

        try:
            logger.debug(f"Getting status for task: {task_id}")

            result = AsyncResult(task_id, app=self.celery_client)

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
            logger.debug(f"Getting result for task: {task_id}")

            result = AsyncResult(task_id, app=self.celery_client)

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
            logger.info(f"Waiting for task {task_id} to complete (timeout: {timeout}s)")

            result = AsyncResult(task_id, app=self.celery_client)

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

            result = AsyncResult(task_id, app=self.celery_client)
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

    def get_active_tasks(self) -> Dict[str, Any]:
        """
        Get information about currently active tasks

        Returns:
            Dict containing active task information
        """

        try:
            logger.debug("Getting active tasks information")

            # Get active tasks from Celery
            inspect = self.celery_client.control.inspect()
            active_tasks = inspect.active()

            if not active_tasks:
                return {
                    "active_tasks": {},
                    "total_active": 0,
                    "message": "No active tasks found"
                }

            total_active = sum(len(tasks) for tasks in active_tasks.values())

            return {
                "active_tasks": active_tasks,
                "total_active": total_active,
                "workers": list(active_tasks.keys())
            }

        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return {
                "active_tasks": {},
                "total_active": 0,
                "error": str(e)
            }


# Singleton instances for common use cases
embedding_client = TaskResultClient("embedding")
default_client = TaskResultClient("default")
