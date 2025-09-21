"""
API endpoints for getting vector embedding task results from external system
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import JSONResponse

from app.schemas.embedding import (
    TaskStatusResponse,
    TaskResultResponse,
    ActiveTasksResponse,
    TaskCancelResponse
)
from app.services.embedding_service import EmbeddingService
from app.utils.api_response import ok, created
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get Task Status",
    description="Get the current status of an embedding task"
)
async def get_task_status(
    task_id: str = Path(..., description="Task identifier")
) -> JSONResponse:
    """
    Get the status of an embedding task

    - **task_id**: Task identifier returned from submit endpoint

    Returns current status, progress information, and metadata
    """

    try:
        logger.debug(f"Getting status for task: {task_id}")

        # Get task status from service
        status_data = EmbeddingService.get_task_status(task_id)

        response_data = TaskStatusResponse(**status_data)

        return ok(
            data=response_data.model_dump(),
            message="Task status retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get(
    "/result/{task_id}",
    response_model=TaskResultResponse,
    summary="Get Task Result",
    description="Get the result of a completed embedding task"
)
async def get_task_result(
    task_id: str = Path(..., description="Task identifier")
) -> JSONResponse:
    """
    Get the result of a completed embedding task

    - **task_id**: Task identifier returned from submit endpoint

    Returns the embedding results if the task is completed successfully
    """

    try:
        logger.debug(f"Getting result for task: {task_id}")

        # Get task result from service
        result_data = EmbeddingService.get_task_result(task_id)

        response_data = TaskResultResponse(**result_data)

        return ok(
            data=response_data.model_dump(),
            message="Task result retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Failed to get task result for {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task result: {str(e)}"
        )





@router.delete(
    "/cancel/{task_id}",
    response_model=TaskCancelResponse,
    summary="Cancel Task",
    description="Cancel a running embedding task"
)
async def cancel_task(
    task_id: str = Path(..., description="Task identifier")
) -> JSONResponse:
    """
    Cancel a running embedding task

    - **task_id**: Task identifier returned from submit endpoint

    Attempts to cancel the task if it's still running
    """

    try:
        logger.info(f"Cancelling task: {task_id}")

        # Cancel task via service
        cancel_data = EmbeddingService.cancel_task(task_id)

        response_data = TaskCancelResponse(**cancel_data)

        return ok(
            data=response_data.model_dump(),
            message="Task cancellation requested"
        )

    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task: {str(e)}"
        )


# @router.get(
#     "/active",
#     response_model=ActiveTasksResponse,
#     summary="Get Active Tasks",
#     description="Get information about currently active embedding tasks"
# )
# async def get_active_tasks() -> JSONResponse:
#     """
#     Get information about currently active embedding tasks

#     Returns information about all active tasks across all workers
#     """

#     try:
#         logger.debug("Getting active tasks information")

#         # Get active tasks from service
#         active_data = EmbeddingService.get_active_tasks()

#         response_data = ActiveTasksResponse(**active_data)

#         return create_success_response(
#             data=response_data.model_dump(),
#             message="Active tasks retrieved successfully"
#         )

#     except Exception as e:
#         logger.error(f"Failed to get active tasks: {e}")
#         return create_error_response(
#             message=f"Failed to get active tasks: {str(e)}",
#             status_code=500
#         )
