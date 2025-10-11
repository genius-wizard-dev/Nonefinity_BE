from fastapi import APIRouter, Depends, Query, status
from fastapi.encoders import jsonable_encoder
from typing import Optional, List, Dict, Any

from app.services.user import user_service
from app.utils.api_response import ok
from app.utils.verify_token import verify_token
from app.crud.task import TaskCRUD
from app.schemas.response import ApiResponse, ApiError
from beanie.odm.fields import PydanticObjectId


router = APIRouter(
    prefix="/tasks",
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


@router.get(
    "/",
    response_model=ApiResponse[List[Dict[str, Any]]],
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
    status: Optional[str] = Query(None, description="Filter by task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED)"),
    task_type: Optional[str] = Query(None, description="Filter by task type (embedding, search)"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    current_user: dict = Depends(verify_token),
):
    """
    List tasks for current user

    This endpoint retrieves a paginated list of tasks owned by the authenticated user.
    Tasks can be filtered by status and type.

    **Query Parameters:**
    - **status**: Filter by task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED)
    - **task_type**: Filter by task type (embedding, search)
    - **skip**: Number of items to skip (pagination)
    - **limit**: Number of items to return (1-100, default: 50)

    **Returns:**
    - List of task objects with complete metadata
    - Each task includes ID, status, type, progress, and timestamps

    **Example Response:**
    ```json
    {
        "success": true,
        "message": "Tasks fetched",
        "data": [
            {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "task_type": "embedding",
                "status": "SUCCESS",
                "progress": 100,
                "result": {
                    "embeddings_count": 100,
                    "processing_time": 45.2
                },
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        ]
    }
    ```

    **Note:**
    - Tasks are returned in reverse chronological order (newest first)
    - Maximum 100 tasks can be returned per request
    - Use pagination for large result sets
    """
    owner_id = await _get_owner_id(current_user)
    crud = TaskCRUD()
    filter_ = {"user_id": owner_id}
    if status:
        filter_["status"] = status
    if task_type:
        filter_["task_type"] = task_type
    tasks = await crud.list(filter_, skip=skip, limit=min(limit, 100))
    data = jsonable_encoder(tasks, custom_encoder={PydanticObjectId: str})
    return ok(data=data, message="Tasks fetched")


