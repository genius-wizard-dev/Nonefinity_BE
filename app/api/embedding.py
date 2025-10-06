"""
API endpoints for creating and managing vector embedding tasks with external AI Tasks System
"""

from fastapi import APIRouter, HTTPException, Path, Depends
from fastapi.responses import JSONResponse

from app.schemas.embedding import (
    EmbeddingRequest,
    SearchRequest,
    TaskResponse,
    TaskStatusResponse,
    TaskResultResponse,
    TaskCancelResponse,
    ActiveTasksResponse
)
from app.services.embedding_service import EmbeddingService
from app.services.model_service import ModelService
from app.services.user import user_service
from app.utils.api_response import ok
from app.utils.logging import get_logger
from app.utils.verify_token import verify_token
from starlette.status import HTTP_400_BAD_REQUEST

logger = get_logger(__name__)

router = APIRouter()


async def get_owner(current_user):
    """Helper function to get owner and embedding service"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    owner_id = str(user.id)

    return owner_id

@router.get(
    "/models",
    summary="Get Embedding Models",
    description="Get all available embedding models for the current user"
)
async def get_embedding_models(
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Get all available embedding models for the current user

    Returns list of embedding models that can be used for creating tasks
    """

    try:
        owner_id = await get_owner(current_user)


        # Initialize model service
        model_service = ModelService()

        # Get embedding models for user
        result = await model_service.get_models(
            owner_id=owner_id,
            skip=0,
            limit=100,
            model_type="embedding",
            active_only=True
        )

        return ok(
            data=result,
            message="Embedding models retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Failed to get embedding models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get embedding models: {str(e)}"
        )


@router.post(
    "/create",
    response_model=TaskResponse,
    summary="Create Embedding Task",
    description="Create an embedding task for text chunks"
)
async def create_embedding_task(
    request: EmbeddingRequest,
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Create an embedding task for file processing

    - **model_id**: AI model identifier from database
    - **file_id**: File identifier to process
    - **chunks**: Optional list of text chunks to embed

    Returns task ID for monitoring progress
    """

    try:
        owner_id = await get_owner(current_user)
        logger.info(f"Creating embedding task for user {owner_id}")

        # Create embedding task
        result = await EmbeddingService.create_embedding_task(
            user_id=owner_id,
            model_id=request.model_id,
            file_id=request.file_id,
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
    response_model=TaskResponse,
    summary="Create Search Task",
    description="Create a similarity search task"
)
async def create_search_task(
    request: SearchRequest,
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Create a similarity search task

    - **credential_id**: Credential identifier for API key
    - **query_text**: Text to search for
    - **provider**: AI provider (default: openai)
    - **model_id**: Model identifier (default: text-embedding-ada-002)
    - **file_id**: Optional filter by file
    - **limit**: Number of results to return (1-100, default: 5)

    Returns task ID for monitoring progress
    """

    try:
        owner_id = await get_owner(current_user)
        logger.info(f"Creating search task for user {owner_id}")

        # Create search task
        result = await EmbeddingService.create_search_task(
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


@router.get(
    "/active",
    response_model=ActiveTasksResponse,
    summary="Get Active Tasks",
    description="Get information about currently active embedding tasks"
)
async def get_active_tasks() -> JSONResponse:
    """
    Get information about currently active embedding tasks

    Returns information about all active tasks across all workers
    """

    try:
        logger.debug("Getting active tasks information")

        # Get active tasks from service
        active_data = EmbeddingService.get_active_tasks()

        response_data = ActiveTasksResponse(**active_data)

        return ok(
            data=response_data.model_dump(),
            message="Active tasks retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active tasks: {str(e)}"
        )
