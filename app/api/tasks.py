from fastapi import APIRouter, Depends, Query, status
from fastapi.encoders import jsonable_encoder
from typing import Optional, Dict, Any
from bson import ObjectId

from app.services.user import user_service
from app.utils.api_response import ok
from app.utils.verify_token import verify_token
from app.crud.task import TaskCRUD
from app.schemas.response import ApiResponse, ApiError
from beanie.odm.fields import PydanticObjectId


router = APIRouter(
    tags=["Tasks"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)


async def _get_owner_id(current_user: dict) -> str:
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    return str(user.id)


@router.get("",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Tasks",
    description="Get a paginated list of tasks for the current user with optional filtering",
    responses={
        200: {"description": "Tasks retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def list_tasks(
    task_status: Optional[str] = Query(None, alias="status", description="Filter by task status (PENDING, STARTED, PROGRESS, SUCCESS, FAILURE, RETRY, REVOKED, CANCELLED, ERROR)"),
    task_type: Optional[str] = Query(None, description="Filter by task type (embedding, search, text_embedding)"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    current_user: dict = Depends(verify_token),
):
    """
    List tasks for current user

    This endpoint retrieves a paginated list of tasks owned by the authenticated user.
    Tasks can be filtered by status and type.

    **Query Parameters:**
    - **status**: Filter by task status (PENDING, STARTED, PROGRESS, SUCCESS, FAILURE, RETRY, REVOKED, CANCELLED, ERROR)
    - **task_type**: Filter by task type (embedding, search, text_embedding)
    - **skip**: Number of items to skip (pagination)
    - **limit**: Number of items to return (1-100, default: 50)

    **Returns:**
    - List of task objects with complete metadata
    - Total count of tasks matching the filter
    - Each task includes ID, status, type, and timestamps

    **Example Response:**
    ```json
    {
        "success": true,
        "message": "Tasks retrieved successfully",
        "data": {
            "tasks": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "task_id": "abc-123-def",
                    "user_id": "507f1f77bcf86cd799439012",
                    "task_type": "embedding",
                    "status": "SUCCESS",
                    "file_id": "507f1f77bcf86cd799439013",
                    "knowledge_store_id": "507f1f77bcf86cd799439014",
                    "provider": "openai",
                    "model_id": "text-embedding-ada-002",
                    "metadata": {
                        "model_name": "OpenAI Ada 002",
                        "result": {
                            "total_chunks": 100,
                            "successful_chunks": 100
                        }
                    },
                    "error": null,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:35:00Z"
                }
            ],
            "total": 150,
            "skip": 0,
            "limit": 50
        }
    }
    ```

    **Note:**
    - Tasks are returned in reverse chronological order (newest first)
    - Maximum 100 tasks can be returned per request
    - Use pagination for large result sets
    """
    try:
        owner_id = await _get_owner_id(current_user)
        crud = TaskCRUD()
        filter_ = {"user_id": owner_id}
        if task_status:
            filter_["status"] = task_status
        if task_type:
            filter_["task_type"] = task_type

        # Get tasks with sorting by created_at descending (newest first)
        tasks = await crud.model.find(filter_).sort("-created_at").skip(skip).limit(min(limit, 100)).to_list()

        # Get total count
        total = await crud.model.find(filter_).count()

        tasks_data = jsonable_encoder(tasks, custom_encoder={PydanticObjectId: str})

        response_data = {
            "tasks": tasks_data,
            "total": total,
            "skip": skip,
            "limit": limit
        }

        return ok(data=response_data, message="Tasks retrieved successfully")
    except Exception as e:
        from app.utils import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error listing tasks: {e}")
        raise


@router.delete("/{task_id}",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Delete Task",
    description="Delete a specific task by ID",
    responses={
        200: {"description": "Task deleted successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Task not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_task(
    task_id: str,
    current_user: dict = Depends(verify_token),
):
    """
    Delete a specific task by ID

    **Path Parameters:**
    - **task_id**: MongoDB document ID of the task to delete

    **Returns:**
    - Success message with deleted task ID

    **Note:**
    - Only the task owner can delete their tasks
    - This only deletes the MongoDB record, not the Celery task result
    """
    try:
        owner_id = await _get_owner_id(current_user)
        crud = TaskCRUD()

        # Get task to verify ownership
        task = await crud.get_one({"_id": ObjectId(task_id), "user_id": owner_id})
        if not task:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or you don't have permission to delete it"
            )

        # Delete task
        await crud.delete(task)

        return ok(
            data={"task_id": task_id, "deleted": True},
            message="Task deleted successfully"
        )
    except Exception as e:
        from app.utils import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error deleting task {task_id}: {e}")
        raise


@router.delete("",
    response_model=ApiResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Clear Tasks",
    description="Clear multiple tasks based on status filter",
    responses={
        200: {"description": "Tasks cleared successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def clear_tasks(
    clear_type: str = Query(..., description="Type of clear operation: 'all', 'success', 'failed', 'completed'"),
    current_user: dict = Depends(verify_token),
):
    """
    Clear multiple tasks based on status filter

    **Query Parameters:**
    - **clear_type**: Type of clear operation
      - `all`: Delete all tasks
      - `success`: Delete only successful tasks
      - `failed`: Delete only failed/error tasks
      - `completed`: Delete all completed tasks (success + failed)

    **Returns:**
    - Number of tasks deleted

    **Example:**
    ```
    DELETE /tasks?clear_type=success
    DELETE /tasks?clear_type=failed
    DELETE /tasks?clear_type=all
    ```
    """
    try:
        owner_id = await _get_owner_id(current_user)
        crud = TaskCRUD()

        # Build filter based on clear_type
        filter_ = {"user_id": owner_id}

        if clear_type == "success":
            filter_["status"] = "SUCCESS"
        elif clear_type == "failed":
            filter_["status"] = {"$in": ["FAILURE", "ERROR", "REVOKED"]}
        elif clear_type == "completed":
            filter_["status"] = {"$in": ["SUCCESS", "FAILURE", "ERROR", "REVOKED"]}
        elif clear_type == "all":
            # No additional filter, will delete all user's tasks
            pass
        else:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid clear_type: {clear_type}. Must be one of: all, success, failed, completed"
            )

        # Get tasks to delete
        tasks_to_delete = await crud.model.find(filter_).to_list()
        deleted_count = 0

        # Delete each task
        for task in tasks_to_delete:
            await crud.delete(task)
            deleted_count += 1

        return ok(
            data={
                "clear_type": clear_type,
                "deleted_count": deleted_count
            },
            message=f"Successfully deleted {deleted_count} task(s)"
        )
    except Exception as e:
        from app.utils import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error clearing tasks: {e}")
        raise


