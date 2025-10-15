"""
API endpoints for creating and managing vector embedding tasks with external AI Tasks System
"""

from fastapi import APIRouter, HTTPException, Path, Depends, status
from fastapi.responses import JSONResponse

from app.schemas.embedding import (
    EmbeddingRequest,
    TextEmbeddingRequest,
    SearchRequest,
    TaskResponse,
    TaskStatusResponse,
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


def create_task_response(result: dict, success_message: str) -> JSONResponse:
    """Helper function to create standardized task response"""
    response_data = TaskResponse(
        success=result["success"],
        task_id=result["task_id"],
        message=result["message"],
        metadata=result.get("metadata")
    )

    return ok(
        data=response_data.model_dump(),
        message=success_message
    )



@router.post(
    "/create",
    response_model=ApiResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Embedding Task",
    description="Create an embedding task for processing files or text into vector embeddings",
    responses={
        202: {"description": "Task created successfully"},
        400: {"description": "Invalid request or missing model configuration"},
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

        return create_task_response(result, "Embedding task created successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create embedding task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create embedding task: {str(e)}"
        )


@router.post(
    "/text",
    response_model=ApiResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Text Embedding Task",
    description="Create an embedding task for processing text into vector embeddings",
    responses={
        202: {"description": "Text embedding task created successfully"},
        400: {"description": "Invalid request or missing model configuration"},
        401: {"description": "Authentication required"},
        500: {"description": "Text embedding task creation failed"}
    }
)
async def create_text_embedding_task(
    request: TextEmbeddingRequest,
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Create a text embedding task

    This endpoint creates an asynchronous task to process text input and generate
    vector embeddings using AI models. The text is split into chunks and embedded
    using the specified model.

    **Parameters:**
    - **text**: Text to embed (required, 1-10000 characters)
    - **model_id**: Model identifier for embedding generation (required)
    - **knowledge_store_id**: Optional knowledge store to store embeddings

    **Process:**
    1. Text is validated and split into appropriate chunks
    2. Chunks are processed using the specified AI model
    3. Vector embeddings are generated and stored in Qdrant
    4. Task progress is tracked and can be monitored

    **Returns:**
    - **task_id**: Unique identifier for monitoring embedding progress
    - **success**: Boolean indicating if task was initiated successfully
    - **message**: Human-readable status message
    - **metadata**: Additional embedding information

    **Example:**
    ```json
    {
        "text": "This is a sample text to embed",
        "model_id": "507f1f77bcf86cd799439011",
        "knowledge_store_id": "507f1f77bcf86cd799439012"
    }
    ```

    **Note:**
    - Text is automatically chunked for optimal embedding
    - Use the task ID to monitor progress via `/status/{task_id}` (polling pattern)
    - Results are included in the status response when task completes
    """
    try:
        owner_id, embedding_service = await get_owner_and_embedding_service(current_user)

        result = await embedding_service.create_text_embedding_task(
            user_id=owner_id,
            text_data=request
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create text embedding task")
            )

        return create_task_response(result, "Text embedding task created successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create text embedding task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create text embedding task: {str(e)}"
        )


@router.post(
    "/search",
    response_model=ApiResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Search Task",
    description="Create a similarity search task to find relevant content using vector embeddings",
    responses={
        202: {"description": "Search task created successfully"},
        400: {"description": "Invalid request or missing model/credential configuration"},
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
    - **provider**: AI provider (openai, google, nvidia, togetherai, groq)
    - **model_id**: Model identifier for embedding generation (required)
    - **credential_id**: Credential ID for API access (required)
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
        "provider": "openai",
        "model_id": "507f1f77bcf86cd799439013",
        "credential_id": "507f1f77bcf86cd799439014",
        "file_id": "507f1f77bcf86cd799439011",
        "limit": 10
    }
    ```

    **Note:**
    - Search results are ranked by similarity score
    - Results include original text chunks and source information
    - Use the task ID to monitor progress via `/status/{task_id}` (polling pattern)
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

        return create_task_response(result, "Search task created successfully")

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
    description="Get the current status of an embedding task. Use this endpoint for polling task progress."
)
async def get_task_status(
    task_id: str = Path(..., description="Task identifier"),
    current_user: dict = Depends(verify_token)
) -> JSONResponse:
    """
    Get the status of an embedding task

    This endpoint is designed for polling by the frontend to check task progress.
    The response includes both status information and results (if completed).

    - **task_id**: Task identifier returned from submit endpoint

    **Polling Pattern:**
    1. Frontend calls this endpoint every few seconds
    2. Check `ready` field to determine if task is complete
    3. If `ready: true`, check `successful` field for completion status
    4. If `successful: true`, use the `result` field for task output

    **Response States:**
    - `PENDING`: Task is waiting to be processed
    - `STARTED`: Task has started processing
    - `PROGRESS`: Task is in progress (check `meta` for progress info)
    - `SUCCESS`: Task completed successfully
    - `FAILURE`: Task failed (check `error` field)
    - `RETRY`: Task is being retried
    - `REVOKED`: Task was cancelled

    Returns current status, progress information, and results (if available)
    """

    try:
        _, embedding_service = await get_owner_and_embedding_service(current_user)
        logger.debug(f"Getting status for task: {task_id}")

        # Get task status from service (use async version for better MongoDB integration)
        status_data = await embedding_service.get_task_status_async(task_id)

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

        # Cancel task via service (use async version for better MongoDB integration)
        cancel_data = await embedding_service.cancel_task_async(task_id)

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

