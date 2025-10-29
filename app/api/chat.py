from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, status, WebSocket, WebSocketDisconnect
from starlette.status import HTTP_400_BAD_REQUEST
import json

from app.schemas.chat import (
    ChatConfigCreate, ChatConfigUpdate, ChatConfigResponse, ChatConfigListResponse,
    ChatSessionCreate, ChatSessionResponse, ChatSessionListResponse,
)
from app.services.chat import ChatService
from app.services.user import user_service
from app.utils.api_response import ok, created, paginated
from app.utils.verify_token import verify_token
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
    current_user: dict = Depends(verify_token)
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
    current_user: dict = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of configs to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of configs to return")
):
    """Get all chat configurations for the current user"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat_configs = await chat_service.get_chat_configs(owner_id, skip, limit)
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
async def get_chat_config(
    config_id: str = Path(..., description="Chat Config ID"),
    current_user: dict = Depends(verify_token)
):
    """Get a specific chat configuration by ID"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat_config = await chat_service.get_chat_config(owner_id, config_id)
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
    current_user: dict = Depends(verify_token)
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
    current_user: dict = Depends(verify_token)
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
    current_user: dict = Depends(verify_token)
):
    """Create a new chat session"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
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
    current_user: dict = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of sessions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of sessions to return")
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
    current_user: dict = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of messages to return")
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
    current_user: dict = Depends(verify_token)
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
    "/sessions/{session_id}/messages",
    status_code=status.HTTP_200_OK,
    summary="Clear Session Messages",
    description="Clear all messages from a chat session"
)
async def clear_session_messages(
    session_id: str = Path(..., description="Chat Session ID"),
    current_user: dict = Depends(verify_token)
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



@router.websocket("/sessions/{session_id}/stream")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    current_user: dict = Depends(verify_token)
):
    await websocket.accept()
    owner_id, chat_service = await get_owner_and_service(current_user)

    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        message = payload.get("message", "")

        await websocket.send_json({
            "type": "start",
            "data": {"message": "WebSocket stream started"}
        })

        async for chunk in chat_service.stream_agent_response(owner_id, session_id, message):
            event_type = chunk.get("event", "message")
            event_data = chunk.get("data", {})

            if event_type == "approval_request":
                await websocket.send_json({"type": "approval_request", "data": event_data})

                while True:
                    client_resp = await websocket.receive_text()
                    resp_data = json.loads(client_resp)

                    if resp_data.get("type") == "approval_response":
                        decision = resp_data["data"]["decision"]
                        await chat_service.handle_approval_response(session_id, decision)
                        break

            else:
                await websocket.send_json({"type": event_type, "data": event_data})

        await websocket.send_json({
            "type": "end",
            "data": {"message": "Stream completed"}
        })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        await websocket.send_json({"type": "error", "data": {"message": str(e)}})

@router.post(
    "/sessions/{session_id}/save-conversation",
    status_code=status.HTTP_201_CREATED,
    summary="Save Conversation Batch",
    description="Save complete conversation flow including tool calls and results"
)
async def save_conversation(
    request: Request,
    session_id: str = Path(..., description="Chat Session ID"),
    current_user: dict = Depends(verify_token)
):
    """Save a batch of messages representing complete conversation flow"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)

        # Parse request body
        body = await request.json()
        messages = body.get('messages', [])

        if not messages:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="No messages provided"
            )

        # Save conversation batch
        success = await chat_service.save_conversation_batch(owner_id, session_id, messages)

        return ok(
            data={"saved": len(messages)},
            message=f"Saved {len(messages)} messages successfully"
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Save conversation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

