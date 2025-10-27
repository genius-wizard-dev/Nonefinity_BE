from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request, status
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST
import json

from app.schemas.chat import (
    ChatCreateRequest, ChatUpdateRequest, ChatResponse, ChatListResponse,
    ChatMessageCreate, ChatMessageResponse
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
    "",
    response_model=ApiResponse[ChatResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Chat",
    description="Create a new chat configuration"
)
async def create_chat(
    request: ChatCreateRequest,
    current_user: dict = Depends(verify_token)
):
    """Create a new chat"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)

        # Convert request to ChatCreate
        from app.schemas.chat import ChatCreate
        chat_data = ChatCreate(**request.model_dump())

        chat = await chat_service.create_chat(owner_id, chat_data)
        return created(data=chat, message="Chat created successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Create chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "",
    response_model=ApiResponse[List[ChatListResponse]],
    summary="List Chats",
    description="Get all chats for the current user"
)
async def list_chats(
    request: Request,
    current_user: dict = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of chats to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of chats to return")
):
    """Get all chats for the current user"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chats = await chat_service.get_chats(owner_id, skip, limit)
        total = await chat_service.count_chats(owner_id)

        # Return consistent structure like Model API
        return ok(
            data={
                "chats": chats,
                "total": total,
                "skip": skip,
                "limit": limit
            },
            message="Chats retrieved successfully"
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"List chats failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{chat_id}",
    response_model=ApiResponse[ChatResponse],
    summary="Get Chat",
    description="Get a specific chat by ID"
)
async def get_chat(
    chat_id: str = Path(..., description="Chat ID"),
    current_user: dict = Depends(verify_token)
):
    """Get a specific chat by ID"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        chat = await chat_service.get_chat(owner_id, chat_id)
        return ok(data=chat, message="Chat retrieved successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Get chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/{chat_id}",
    response_model=ApiResponse[ChatResponse],
    summary="Update Chat",
    description="Update a chat configuration"
)
async def update_chat(
    request: ChatUpdateRequest,
    chat_id: str = Path(..., description="Chat ID"),
    current_user: dict = Depends(verify_token)
):
    """Update a chat"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)

        # Convert request to ChatUpdate
        from app.schemas.chat import ChatUpdate
        chat_data = ChatUpdate(**request.model_dump(exclude_unset=True))

        chat = await chat_service.update_chat(owner_id, chat_id, chat_data)
        return ok(data=chat, message="Chat updated successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Update chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{chat_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Chat",
    description="Delete a chat and its history"
)
async def delete_chat(
    chat_id: str = Path(..., description="Chat ID"),
    current_user: dict = Depends(verify_token)
):
    """Delete a chat"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        await chat_service.delete_chat(owner_id, chat_id)
        return ok(message="Chat deleted successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Delete chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Chat message endpoints
@router.post(
    "/{chat_id}/messages",
    response_model=ApiResponse[ChatMessageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Message",
    description="Add a message to chat history"
)
async def add_message(
    message_data: ChatMessageCreate,
    chat_id: str = Path(..., description="Chat ID"),
    current_user: dict = Depends(verify_token)
):
    """Add a message to chat history"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        message = await chat_service.add_message(owner_id, chat_id, message_data)
        return created(data=message, message="Message added successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Add message failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{chat_id}/messages",
    response_model=ApiResponse[List[ChatMessageResponse]],
    summary="Get Messages",
    description="Get chat messages with pagination"
)
async def get_messages(
    chat_id: str = Path(..., description="Chat ID"),
    current_user: dict = Depends(verify_token),
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of messages to return")
):
    """Get chat messages"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        messages = await chat_service.get_messages(owner_id, chat_id, skip, limit)
        return ok(data=messages, message="Messages retrieved successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Get messages failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/{chat_id}/messages",
    response_model=ApiResponse[ChatResponse],
    status_code=status.HTTP_200_OK,
    summary="Clear History",
    description="Clear all messages from chat history"
)
async def clear_history(
    chat_id: str = Path(..., description="Chat ID"),
    current_user: dict = Depends(verify_token)
):
    """Clear chat history"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)
        updated_chat = await chat_service.clear_history(owner_id, chat_id)
        return ok(data=updated_chat, message="Chat history cleared successfully")

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Clear history failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Streaming endpoint
@router.post(
    "/{chat_id}/stream",
    summary="Stream Chat Response",
    description="Send a message and receive streaming response (SSE)"
)
async def stream_chat(
    message_data: ChatMessageCreate,
    chat_id: str = Path(..., description="Chat ID"),
    current_user: dict = Depends(verify_token)
):
    """Stream chat response using Server-Sent Events"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)

        # Verify chat exists
        chat = await chat_service.crud.get_by_owner_and_id(owner_id, chat_id)
        if not chat:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Chat not found"
            )

        # Create streaming generator
        async def event_generator():
            try:
                # Send start event
                yield f"event: start\ndata: {json.dumps({'message': 'Stream started'})}\n\n"

                # Stream agent response
                async for chunk in chat_service.stream_agent_response(owner_id, chat_id, message_data.content):
                    event_type = chunk.get("event", "message")
                    event_data = chunk.get("data", {})

                    # Send event with proper SSE format
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

                # Send end event
                yield f"event: end\ndata: {json.dumps({'message': 'Stream completed'})}\n\n"

            except Exception as e:
                logger.error(f"Streaming error: {str(e)}")
                logger.exception(e)
                yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Stream chat failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Approval endpoint for tool execution
@router.post(
    "/{chat_id}/approve",
    summary="Approve/Reject/Edit Tool Execution",
    description="Handle user decision for tool execution approval"
)
async def approve_tool_execution(
    request: Request,
    chat_id: str = Path(..., description="Chat ID"),
    current_user: dict = Depends(verify_token)
):
    """Handle tool execution approval, rejection, or editing"""
    try:
        owner_id, chat_service = await get_owner_and_service(current_user)

        # Verify chat exists
        chat = await chat_service.crud.get_by_owner_and_id(owner_id, chat_id)
        if not chat:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="Chat not found"
            )

        # Parse request body
        body = await request.json()
        decision_type = body.get('type', 'approve')  # approve, reject, or edit
        resume_data = body.get('resume_data')  # Resume data structure

        # Create streaming generator for resumed execution
        async def event_generator():
            try:
                yield f"event: resume\ndata: {json.dumps({'message': 'Resuming execution'})}\n\n"

                # Stream agent response with resume data
                async for chunk in chat_service.stream_agent_response(
                    owner_id, chat_id, "", resume_data=resume_data
                ):
                    event_type = chunk.get("event", "message")
                    event_data = chunk.get("data", {})
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"

                yield f"event: end\ndata: {json.dumps({'message': 'Stream completed'})}\n\n"

            except Exception as e:
                logger.error(f"Approval streaming error: {str(e)}")
                logger.exception(e)
                yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )

    except HTTPException:
        raise
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Approve tool execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Batch save conversation
@router.post(
    "/{chat_id}/save-conversation",
    status_code=status.HTTP_201_CREATED,
    summary="Save Conversation Batch",
    description="Save complete conversation flow including tool calls and results"
)
async def save_conversation(
    request: Request,
    chat_id: str = Path(..., description="Chat ID"),
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
        success = await chat_service.save_conversation_batch(owner_id, chat_id, messages)

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
