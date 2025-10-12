"""
API endpoints for creating and managing vector embedding tasks with external AI Tasks System
"""

from fastapi import APIRouter, HTTPException, Path, Depends, status
from fastapi.responses import JSONResponse

from app.schemas.embedding import (
    EmbeddingRequest,
    SearchRequest,
    TaskResponse,
    TaskStatusResponse,
    TaskResultResponse,
    TaskCancelResponse
)
from app.schemas.response import ApiResponse, ApiError
from app.services.embedding_service import EmbeddingService
from app.services.user import user_service
from app.utils.api_response import ok
from app.utils.logging import get_logger
from app.utils.verify_token import verify_token
from starlette.status import HTTP_400_BAD_REQUEST

logger = get_logger(__name__)

router = APIRouter(
    tags=["Embeddings"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)

async def get_owner_and_embedding_service(current_user):
    """Helper function to get owner and embedding service"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST,
                            detail="User not found")

    owner_id = str(user.id)
    embedding_service = EmbeddingService()

    return owner_id, embedding_service

@router.post(
    "/create",
    response_model=ApiResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Embedding Task",
    description="Create an embedding task for processing files or text into vector embeddings",
    responses={
        202: {"description": "Task created successfully"},
        400: {"description": "Invalid request or file not found"},
        401: {"description": "Authentication required"},
        500: {"description": "Task creation failed"}
    }
)
async def create_embedding_task(
    request: EmbeddingRequest,
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    try:
        owner_id, embedding_service = await get_owner_and_embedding_service(current_user)

        result = await embedding_service.create_embedding_task(
            user_id=owner_id,
            embedding_data=request
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create embedding task")
            )

        response_data = TaskResponse(
            success=result["success"],
            task_id=result["task_id"],
            message=result["message"],
            metadata=result.get("metadata")
        )

        return ok(
            data=response_data.model_dump(),
            message="Embedding task created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create embedding task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create embedding task: {str(e)}"
        )


@router.post(
    "/search",
    response_model=ApiResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Search Task",
    description="Create a similarity search task to find relevant content using vector embeddings",
    responses={
        202: {"description": "Search task created successfully"},
        400: {"description": "Invalid request or missing credentials"},
        401: {"description": "Authentication required"},
        500: {"description": "Search task creation failed"}
    }
)
async def create_search_task(
    request: SearchRequest,
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Create a similarity search task

    This endpoint creates an asynchronous task to perform semantic search across
    previously embedded content. The search uses vector similarity to find the
    most relevant content based on the query text.

    **Parameters:**
    - **query_text**: Text to search for (required)
    - **provider**: AI provider (huggingface, openai, local)
    - **model_id**: Model identifier for embedding generation
    - **credential_id**: Optional credential ID for API access
    - **file_id**: Optional filter to search within specific file
    - **limit**: Number of results to return (1-100, default: 5)

    **Process:**
    1. Query text is converted to vector embedding
    2. Vector similarity search is performed against stored embeddings
    3. Most relevant chunks are returned with similarity scores
    4. Results include original text and metadata

    **Returns:**
    - **task_id**: Unique identifier for monitoring search progress
    - **success**: Boolean indicating if search was initiated successfully
    - **message**: Human-readable status message
    - **metadata**: Additional search information

    **Example:**
    ```json
    {
        "query_text": "machine learning algorithms",
        "provider": "huggingface",
        "model_id": "sentence-transformers/all-MiniLM-L6-v2",
        "file_id": "507f1f77bcf86cd799439011",
        "limit": 10
    }
    ```

    **Note:**
    - Search results are ranked by similarity score
    - Results include original text chunks and source information
    - Use the task ID to retrieve results via `/result/{task_id}`
    """

    try:
        owner_id, embedding_service = await get_owner_and_embedding_service(current_user)
        logger.info(f"Creating search task for user {owner_id}")

        # Create search task
        result = await embedding_service.create_search_task(
            user_id=owner_id,
            credential_id=request.credential_id,
            query_text=request.query_text,
            provider=request.provider,
            model_id=request.model_id,
            file_id=request.file_id,
            limit=request.limit
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create search task")
            )

        response_data = TaskResponse(
            success=result["success"],
            task_id=result["task_id"],
            message=result["message"],
            metadata=result.get("metadata")
        )

        return ok(
            data=response_data.model_dump(),
            message="Search task created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create search task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create search task: {str(e)}"
        )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get Task Status",
    description="Get the current status of an embedding task"
)
async def get_task_status(
    task_id: str = Path(..., description="Task identifier"),
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Get the status of an embedding task

    - **task_id**: Task identifier returned from submit endpoint

    Returns current status, progress information, and metadata
    """

    try:
        _, embedding_service = await get_owner_and_embedding_service(current_user)
        logger.debug(f"Getting status for task: {task_id}")

        # Get task status from service
        status_data = embedding_service.get_task_status(task_id)

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
    task_id: str = Path(..., description="Task identifier"),
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Get the result of a completed embedding task

    - **task_id**: Task identifier returned from submit endpoint

    Returns the embedding results if the task is completed successfully
    """

    try:
        logger.debug(f"Getting result for task: {task_id}")
        owner_id, embedding_service = await get_owner_and_embedding_service(current_user)

        # Get task result from service
        result_data = embedding_service.get_task_result(task_id)

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
    task_id: str = Path(..., description="Task identifier"),
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Cancel a running embedding task

    - **task_id**: Task identifier returned from submit endpoint

    Attempts to cancel the task if it's still running
    """

    try:
        owner_id, embedding_service = await get_owner_and_embedding_service(current_user)
        logger.info(f"Cancelling task: {task_id}")

        # Cancel task via service
        cancel_data = embedding_service.cancel_task(task_id)

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
# async def get_active_tasks(current_user: dict = Depends(verify_token)) -> JSONResponse:
#     """
#     Get information about currently active embedding tasks

#     Returns information about all active tasks across all workers
#     """

#     try:
#         owner_id, embedding_service = await get_owner_and_embedding_service(current_user)
#         logger.debug("Getting active tasks information")

#         # Get active tasks from service
#         active_data = embedding_service.get_active_tasks()

#         response_data = ActiveTasksResponse(**active_data)

#         return ok(
#             data=response_data.model_dump(),
#             message="Active tasks retrieved successfully"
#         )

#     except Exception as e:
#         logger.error(f"Failed to get active tasks: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to get active tasks: {str(e)}"
#         )
