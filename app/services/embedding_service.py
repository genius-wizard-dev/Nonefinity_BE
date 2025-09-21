"""
Service for getting vector embedding task results from external Celery system
"""

from typing import Dict, Any, Optional

from app.utils.celery_client import embedding_client
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service class for getting embedding task results from external system"""

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
