from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, status
from typing import List
from starlette.status import HTTP_400_BAD_REQUEST
from starlette.responses import StreamingResponse
from pydantic import BaseModel
import json

from app.schemas.chat import (
    ChatConfigCreate, ChatConfigUpdate, ChatConfigResponse, ChatConfigListResponse,
    ChatSessionCreate, ChatSessionResponse, ChatSessionListResponse,
    SaveConversationRequest,
)
from app.services.chat import ChatService
from app.services.user import user_service
from app.utils.api_response import ok, created
from app.utils.api_key_auth import verify_api_key_or_token, validate_chat_config_access
from app.schemas.response import ApiResponse, ApiError
from app.core.exceptions import AppError
from app.utils import get_logger
logger = get_logger(__name__)

router = APIRouter(
    tags=["Chats"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)


async def get_owner_and_service(current_user):
    """Helper function to get owner ID and chat service"""
    # API keys already contain owner_id in 'sub'
    if current_user.get("auth_type") == "api_key":
        owner_id = current_user.get("sub")
    else:
        # JWT tokens contain clerk_id in 'sub', need to look up user
        clerk_id = current_user.get("sub")
        user = await user_service.crud.get_by_clerk_id(clerk_id)
        if not user:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="User not found"
            )
        owner_id = str(user.id)

    chat_service = ChatService()
    return owner_id, chat_service


@router.post(
    "/configs",
    response_model=ApiResponse[ChatConfigResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Chat Config",
    description="Create a new chat configuration"
)
async def create_chat_config(
    request: ChatConfigCreate,
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Create a new chat configuration"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat_config = await chat_service.create_chat_config(owner_id, request)
        return created(data=chat_config, message="Chat config created successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Create chat config failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/configs",
    response_model=ApiResponse[ChatConfigListResponse],
    summary="List Chat Configs",
    description="Get all chat configurations for the current user"
)
async def list_chat_configs(
    request: Request,
    current_user: dict = Depends(verify_api_key_or_token),
    skip: int = Query(0, ge=0, description="Number of configs to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Number of configs to return")
):
    """Get all chat configurations for the current user"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat_configs = await chat_service.get_list_chat_configs(owner_id, skip, limit)
        return ok(data=chat_configs, message="Chat configs retrieved successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"List chat configs failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/configs/{config_id}",
    response_model=ApiResponse[ChatConfigResponse],
    summary="Get Chat Config",
    description="Get a specific chat configuration by ID"
)
async def get_chat_config_by_id(
    config_id: str = Path(..., description="Chat Config ID"),
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Get a specific chat configuration by ID"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat_config = await chat_service.get_chat_config_by_id(owner_id, config_id)
        return ok(data=chat_config, message="Chat config retrieved successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Get chat config failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/configs/{config_id}",
    response_model=ApiResponse[ChatConfigResponse],
    summary="Update Chat Config",
    description="Update a chat configuration"
)
async def update_chat_config(
    request: ChatConfigUpdate,
    config_id: str = Path(..., description="Chat Config ID"),
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Update a chat configuration"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat_config = await chat_service.update_chat_config(owner_id, config_id, request)
        return ok(data=chat_config, message="Chat config updated successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Update chat config failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/configs/{config_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Chat Config",
    description="Delete a chat configuration"
)
async def delete_chat_config(
    config_id: str = Path(..., description="Chat Config ID"),
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Delete a chat configuration"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        await chat_service.delete_chat_config(owner_id, config_id)
        return ok(message="Chat config deleted successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Delete chat config failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Chat session endpoints
@router.post(
    "/sessions",
    response_model=ApiResponse[ChatSessionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Chat Session",
    description="Create a new chat session"
)
async def create_chat_session(
    request: ChatSessionCreate,
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Create a new chat session"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)

        # Validate API key has access to this chat config
        validate_chat_config_access(current_user, request.chat_config_id)

        chat_session = await chat_service.create_chat_session(owner_id, request)
        return created(data=chat_session, message="Chat session created successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Create chat session failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/sessions",
    response_model=ApiResponse[ChatSessionListResponse],
    summary="List Chat Sessions",
    description="Get all chat sessions for the current user"
)
async def list_chat_sessions(
    request: Request,
    current_user: dict = Depends(verify_api_key_or_token),
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Number of sessions to return")
):
    """Get all chat sessions for the current user"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat_sessions = await chat_service.get_chat_sessions(owner_id, skip, limit)
        return ok(data=chat_sessions, message="Chat sessions retrieved successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"List chat sessions failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/sessions/{session_id}",
    response_model=ApiResponse[ChatSessionResponse],
    summary="Get Chat Session",
    description="Get a specific chat session with messages"
)
async def get_chat_session(
    session_id: str = Path(..., description="Chat Session ID"),
    current_user: dict = Depends(verify_api_key_or_token),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Number of messages to return")
):
    """Get a specific chat session with messages"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat_session = await chat_service.get_chat_session(owner_id, session_id, skip, limit)
        return ok(data=chat_session, message="Chat session retrieved successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Get chat session failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Chat Session",
    description="Delete a chat session and its messages"
)
async def delete_chat_session(
    session_id: str = Path(..., description="Chat Session ID"),
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Delete a chat session"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        await chat_service.delete_chat_session(owner_id, session_id)
        return ok(message="Chat session deleted successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Delete chat session failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/sessions",
    status_code=status.HTTP_200_OK,
    summary="Delete Multiple Chat Sessions",
    description="Delete multiple chat sessions and their messages"
)
async def delete_chat_sessions(
    session_ids: List[str] = Query(...,
                                   description="List of chat session IDs to delete"),
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Delete multiple chat sessions"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        result = await chat_service.delete_chat_sessions(owner_id, session_ids)

        message = f"Deleted {result['deleted_count']} chat sessions"
        if result['not_found']:
            message += f". {len(result['not_found'])} sessions not found"

        return ok(data=result, message=message)

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Delete chat sessions failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/sessions/{session_id}/messages",
    status_code=status.HTTP_200_OK,
    summary="Clear Session Messages",
    description="Clear all messages from a chat session"
)
async def clear_session_messages(
    session_id: str = Path(..., description="Chat Session ID"),
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Clear all messages from a chat session"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        await chat_service.delete_chat_session_messages(owner_id, session_id)
        return ok(message="Session messages cleared successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Clear session messages failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


class StreamMessageRequest(BaseModel):
    role: str = "user"
    content: str


def format_sse_message(event_type: str, data: dict) -> str:
    """Format data as Server-Sent Event message"""
    json_data = json.dumps(data)
    if event_type:
        return f"event: {event_type}\ndata: {json_data}\n\n"
    else:
        return f"data: {json_data}\n\n"


async def stream_sse_response(generator):
    """Helper to yield SSE formatted messages from async generator"""
    try:
        async for chunk in generator:
            event_type = chunk.get("event", "message")
            event_data = chunk.get("data", {})
            yield format_sse_message(event_type, event_data)
    except Exception as e:
        logger.error(f"SSE streaming error: {str(e)}")
        error_data = {"message": str(e)}
        yield format_sse_message("error", error_data)


@router.post(
    "/sessions/{session_id}/stream",
    summary="Stream Chat Response",
    description="Stream chat response using Server-Sent Events (SSE). Supports both JWT and API key authentication."
)
async def stream_chat(
    request: StreamMessageRequest,
    session_id: str = Path(..., description="Chat Session ID"),
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Stream chat response using SSE"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        message = request.content

        async def generate_sse():
            # Send start event
            yield format_sse_message(None, "[START]")

            # Stream agent response
            async for chunk in chat_service.stream_agent_response(owner_id, session_id, message):
                event_type = chunk.get("event", "message")
                event_data = chunk.get("data", {})

                yield format_sse_message(event_type, event_data)

            # Send end event if stream completed normally
            yield format_sse_message(None, "[END]")

        return StreamingResponse(
            generate_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except AppError as e:
        async def error_sse(e):
            yield format_sse_message("error", {"message": e.message})
        return StreamingResponse(
            error_sse(e),
            media_type="text/event-stream",
            status_code=e.status_code
        )
    except Exception as e:
        logger.error(f"Stream chat failed: {str(e)}")

        async def error_sse(e):
            yield format_sse_message("error", {"message": e.message})
        return StreamingResponse(
            error_sse(e),
            media_type="text/event-stream",
            status_code=500
        )


@router.post(
    "/sessions/{session_id}/save-conversation",
    status_code=status.HTTP_201_CREATED,
    summary="Save Conversation Batch",
    description="Save complete conversation flow including tool calls and results"
)
async def save_conversation(
    request: SaveConversationRequest,
    session_id: str = Path(..., description="Chat Session ID"),
    current_user: dict = Depends(verify_api_key_or_token)
):
    """Save a batch of messages representing complete conversation flow"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)

        success = await chat_service.save_conversation_batch(owner_id, session_id, request.messages)
        if not success:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Failed to save conversation"
            )
        return ok(
            data={"saved": len(request.messages)},
            message=f"Saved {len(request.messages)} messages successfully"
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Save conversation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
