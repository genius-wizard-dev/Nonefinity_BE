from typing import List, Optional

from app.crud.chat import chat_config_crud, chat_session_crud, chat_message_crud
from app.models.chat import ChatConfig, ChatSession, ChatMessage
from app.schemas.chat import (
    ChatConfigCreate, ChatConfigUpdate, ChatConfigResponse, ChatConfigListResponse,
    ChatSessionCreate, ChatSessionResponse, ChatSessionListResponse,
    ChatMessageCreate, ChatMessageResponse, ChatMessageListResponse
)
from app.core.exceptions import AppError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from app.utils import get_logger
from app.agents.main import get_agent_for_thread, agent_manager, get_agent
from app.agents.llms import LLMConfig
from app.agents.tools import dataset_tools
from app.crud.model import ModelCRUD
from app.crud.credential import CredentialCRUD
from langchain_core.messages import HumanMessage
from langchain.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig

from app.services.provider_service import ProviderService
from app.crud.user import UserCRUD
from app.services.credential_service import CredentialService
from langgraph.types import Interrupt
logger = get_logger(__name__)


class ChatService:
    """Service for chat operations"""

    def __init__(self):
        self.chat_config_crud = chat_config_crud
        self.chat_session_crud = chat_session_crud
        self.chat_message_crud = chat_message_crud
        self._model_crud = ModelCRUD()
        self._credential_crud = CredentialCRUD()
        self._provider_service = ProviderService()
        self._user_crud = UserCRUD()
        self._credential_service = CredentialService()

    async def create_chat_config(self, owner_id: str, chat_config_data: ChatConfigCreate) -> ChatConfigResponse:
        """Create a new chat configuration  """
        # Check if chat name already exists for this owner
        existing_chat_config = await self.chat_config_crud.get_by_name(chat_config_data.name, owner_id)
        if existing_chat_config:
            raise AppError(
                message="Chat config with this name already exists",
                status_code=HTTP_400_BAD_REQUEST
            )

        # Validate configuration
        if chat_config_data.embedding_model_id and not chat_config_data.knowledge_store_id:
            raise AppError(
                message="Knowledge store ID is required when embedding model is provided",
                status_code=HTTP_400_BAD_REQUEST
            )

        if chat_config_data.knowledge_store_id and not chat_config_data.embedding_model_id:
            raise AppError(
                message="Embedding model ID is required when knowledge store is provided",
                status_code=HTTP_400_BAD_REQUEST
            )

        # Create chat
        chat_config = await self.chat_config_crud.create(chat_config_data, owner_id=owner_id)
        return ChatConfigResponse(
            id=str(chat_config.id),
            name=chat_config.name,
            owner_id=chat_config.owner_id,
            chat_model_id=chat_config.chat_model_id,
            embedding_model_id=chat_config.embedding_model_id,
            knowledge_store_id=chat_config.knowledge_store_id,
            instruction_prompt=chat_config.instruction_prompt,
        )


    async def get_chat_config(self, owner_id: str, chat_config_id: str) -> ChatConfigResponse:
        """Get a specific chat by ID"""
        chat_config = await self.chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)
        if not chat_config:
            raise AppError(message="Chat config not found", status_code=HTTP_404_NOT_FOUND)

        return ChatConfigResponse(
            id=str(chat_config.id),
            name=chat_config.name,
            owner_id=chat_config.owner_id,
            chat_model_id=chat_config.chat_model_id,
            embedding_model_id=chat_config.embedding_model_id,
            knowledge_store_id=chat_config.knowledge_store_id,
            instruction_prompt=chat_config.instruction_prompt,
        )

    async def get_chat_configs(self, owner_id: str, skip: int = 0, limit: int = 100) -> List[ChatConfigResponse]:
        """Get all chats for a user"""
        chat_configs = await self.chat_config_crud.list(owner_id=owner_id, skip=skip, limit=limit)
        return ChatConfigListResponse(
            chat_configs=chat_configs,
            total=len(chat_configs),
            skip=skip,
            limit=limit
        )

    async def update_chat_config(self, owner_id: str, chat_config_id: str, chat_config_data: ChatConfigUpdate) -> ChatConfigResponse:
        """Update a chat configuration"""
        chat_config = await self.chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)
        if not chat_config:
            raise AppError(message="Chat config not found", status_code=HTTP_404_NOT_FOUND)

        update_dict = chat_config_data.model_dump(exclude_unset=True)
        if 'name' in update_dict and update_dict['name'] != chat_config.name:
            existing_chat_config = await self.chat_config_crud.get_by_name(update_dict['name'], owner_id)
            if existing_chat_config and str(existing_chat_config.id) != chat_config_id:
                raise AppError(
                    message="Chat config with this name already exists",
                    status_code=HTTP_400_BAD_REQUEST
                )

        # Validate configuration updates
        if "embedding_model_id" in update_dict or "knowledge_store_id" in update_dict:
            new_embedding_model_id = update_dict.get("embedding_model_id", chat_config.embedding_model_id)
            new_knowledge_store_id = update_dict.get("knowledge_store_id", chat_config.knowledge_store_id)

            if new_embedding_model_id and not new_knowledge_store_id:
                raise AppError(
                    message="Knowledge store ID is required when embedding model is provided",
                    status_code=HTTP_400_BAD_REQUEST
                )

            if new_knowledge_store_id and not new_embedding_model_id:
                raise AppError(
                    message="Embedding model ID is required when knowledge store is provided",
                    status_code=HTTP_400_BAD_REQUEST
                )

        # Update chat
        # Handle None values explicitly for embedding_model_id and knowledge_store_id
        if 'embedding_model_id' in update_dict:
            chat_config.embedding_model_id = update_dict['embedding_model_id']
        if 'knowledge_store_id' in update_dict:
            chat_config.knowledge_store_id = update_dict['knowledge_store_id']

        # Update other fields normally
        for key, value in update_dict.items():
            if key not in ['embedding_model_id', 'knowledge_store_id'] and value is not None:
                setattr(chat_config, key, value)

        # Save the chat object directly to handle None values
        await chat_config.save()
        return ChatConfigResponse(
            id=str(chat_config.id),
            name=chat_config.name,
            owner_id=chat_config.owner_id,
            chat_model_id=chat_config.chat_model_id,
            embedding_model_id=chat_config.embedding_model_id,
            knowledge_store_id=chat_config.knowledge_store_id,
            instruction_prompt=chat_config.instruction_prompt,
        )

    async def delete_chat_config(self, owner_id: str, chat_config_id: str) -> bool:
        """Delete a chat configuration"""
        chat_config = await self.chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)
        if not chat_config:
            raise AppError(message="Chat config not found", status_code=HTTP_404_NOT_FOUND)
        await self.chat_config_crud.delete_by_chat_config_id(chat_config_id)
        return True

    async def create_chat_session(self, owner_id: str, chat_session_data: ChatSessionCreate) -> ChatSessionResponse:
        """Create a new chat session"""
        chat_session = await self.chat_session_crud.create(chat_session_data, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Failed to create chat session", status_code=HTTP_400_BAD_REQUEST)
        chat_config = await self.chat_config_crud.get_by_id(id=chat_session.chat_config_id, owner_id=owner_id)
        if not chat_config:
            raise AppError(message="Chat config not found", status_code=HTTP_404_NOT_FOUND)
        model = await self._model_crud.get_by_id(id=chat_config.chat_model_id, owner_id=owner_id)
        if not model:
            raise AppError(message="Model not found", status_code=HTTP_404_NOT_FOUND)
        credential = await self._credential_crud.get_by_id(id=model.credential_id, owner_id=owner_id)
        if not credential:
            raise AppError(message="Credential not found", status_code=HTTP_404_NOT_FOUND)
        api_key = self._credential_service._decrypt_api_key(credential.api_key)
        base_url = credential.base_url if credential.base_url else None
        provider = await self._provider_service.get_provider_by_id(credential.provider_id)
        if not provider:
            raise AppError(message="Provider not found", status_code=HTTP_404_NOT_FOUND)
        llm_config = LLMConfig(model=model.model, provider=provider.provider, api_key=api_key, base_url=base_url)
        if chat_config.dataset_ids:
            tools = dataset_tools
        else:
            tools = []
        agent = await get_agent_for_thread(str(chat_session.id), tools, llm_config, [])
        if not agent:
            raise AppError(message="Failed to create agent", status_code=HTTP_400_BAD_REQUEST)
        return ChatSessionResponse(
            id=str(chat_session.id),
            chat_config_id=chat_session.chat_config_id,
            owner_id=chat_session.owner_id,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
        )

    async def get_chat_session(self, owner_id: str, chat_session_id: str, skip: int = 0, limit: int = 100) -> ChatSessionResponse:
        """Get a specific chat session"""
        chat_session = await self.chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Chat session not found", status_code=HTTP_404_NOT_FOUND)
        messages = await self.chat_message_crud.list(session_id=chat_session_id, owner_id=owner_id, skip=skip, limit=limit)
        return ChatSessionResponse(
            id=str(chat_session.id),
            chat_config_id=chat_session.chat_config_id,
            owner_id=chat_session.owner_id,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            messages=ChatMessageListResponse(
                chat_messages=messages,
                total=len(messages),
                skip=skip,
                limit=limit
            )
        )

    async def get_chat_sessions(self, owner_id: str, skip: int = 0, limit: int = 100) -> List[ChatSessionResponse]:
        """Get all chat sessions for a user"""
        chat_sessions = await self.chat_session_crud.list(owner_id=owner_id, skip=skip, limit=limit)
        return ChatSessionListResponse(
            chat_sessions=chat_sessions,
            total=len(chat_sessions),
            skip=skip,
            limit=limit
        )

    async def delete_chat_session(self, owner_id: str, chat_session_id: str) -> bool:
        """Delete a chat session"""
        chat_session = await self.chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Chat session not found", status_code=HTTP_404_NOT_FOUND)
        await self.chat_session_crud.delete_by_chat_session_id
        (chat_session_id)
        return True

    async def delete_chat_session_messages(self, owner_id: str, chat_session_id: str) -> bool:
        """Delete all messages for a chat session"""
        messages = await self.chat_message_crud.list(session_id=chat_session_id, owner_id=owner_id)
        if not messages:
            raise AppError(message="No messages found", status_code=HTTP_404_NOT_FOUND)
        await self.chat_message_crud.delete_by_chat_session_id(chat_session_id)
        return True

    async def create_chat_message(self, owner_id: str, chat_session_id: str, chat_message_data: ChatMessageCreate) -> ChatMessageResponse:
        """Create a new chat message"""
        chat_message = await self.chat_message_crud.create(chat_message_data, session_id=chat_session_id, owner_id=owner_id)
        return ChatMessageResponse(
            id=str(chat_message.id),
            session_id=chat_message.session_id,
            owner_id=chat_message.owner_id,
            created_at=chat_message.created_at,
            updated_at=chat_message.updated_at,
        )

    async def save_conversation_batch(self, owner_id: str, session_id: str, messages: List[dict]) -> bool:
        """Save a batch of messages representing complete conversation flow"""
        try:
            # Verify session exists
            chat_session = await self.chat_session_crud.get_by_id(id=session_id, owner_id=owner_id)
            if not chat_session:
                raise AppError(
                    message="Chat session not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            # Create messages from batch data
            for message_data in messages:
                chat_message_data = ChatMessageCreate(
                    session_id=session_id,
                    role=message_data.get('role', 'user'),
                    content=message_data.get('content', ''),
                    models=message_data.get('models', {}),
                    tools=message_data.get('tools', {}),
                    interrupt=message_data.get('interrupt', {})
                )
                await self.chat_message_crud.create(chat_message_data, session_id=session_id, owner_id=owner_id)

            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Save conversation batch failed: {str(e)}")
            logger.exception(e)
            raise AppError(
                message=f"Failed to save conversation batch: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )



    async def stream_agent_response(self, owner_id: str, chat_session_id: str, message: str):
        """Stream agent response as async generator

        Args:
            owner_id: User ID
            chat_session_id: Chat session ID
            message: User message
        """
        try:
            user = await self._user_crud.get_by_id(owner_id)
            if not user:
                raise AppError(
                    message="User not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            chat_session = await self.chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
            if not chat_session:
                raise AppError(
                    message="Chat session not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            agent = await get_agent(chat_session_id)
            if not agent:
                raise AppError(
                    message="Agent not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            config = RunnableConfig(configurable={"thread_id": chat_session_id})
            messages_input = {"messages": [HumanMessage(content=message)]}
            for chunk in agent.stream(messages_input, config=config, stream_mode="updates"):
                for step, data in chunk.items():
                    # Skip internal steps
                    if step == "HumanInTheLoopMiddleware.after_model":
                        continue

                    # Handle __interrupt__ for approval requests
                    if step == "__interrupt__":
                        if isinstance(data, tuple) and isinstance(data[0], Interrupt):
                            interrupt_value = data[0].value
                            action_requests = interrupt_value.get('action_requests', [])
                            review_configs = interrupt_value.get('review_configs', [])
                            interrupt_id = data[0].id

                            for idx, action in enumerate(action_requests):
                                review_config = review_configs[idx] if idx < len(review_configs) else {}
                                yield {
                                    "event": "approval_request",
                                    "data": {
                                        "id": str(interrupt_id),
                                        "step": step,
                                        "tool_name": action.get('name', 'unknown'),
                                        "args": action.get('args', {}),
                                        "description": action.get('description', ''),
                                        "allowed_decisions": review_config.get('allowed_decisions', ['approve', 'reject', 'edit']),
                                    }
                                }
                        continue

                    # Handle model and tools steps
                    try:
                        if 'messages' not in data or not data['messages']:
                            continue

                        message = data['messages'][-1]

                        # Handle AIMessage (from model)
                        if step == "model" and hasattr(message, 'tool_calls'):
                            # AI is making tool calls
                            if message.tool_calls:
                                for tool_call in message.tool_calls:
                                    yield {
                                        "event": "tool_call",
                                        "data": {
                                            "id": tool_call.get('id', ''),
                                            "step": step,
                                            "tool_name": tool_call.get('name', ''),
                                            "args": tool_call.get('args', {}),
                                            "status": "pending"
                                        }
                                    }
                            # AI is responding with text
                            elif hasattr(message, 'content') and message.content:
                                # Extract text content from message
                                content_text = ""
                                if isinstance(message.content, str):
                                    content_text = message.content
                                elif isinstance(message.content, list):
                                    # Handle content blocks format
                                    for block in message.content:
                                        if isinstance(block, dict) and block.get('type') == 'text':
                                            content_text += block.get('text', '')
                                        elif isinstance(block, str):
                                            content_text += block

                                if content_text:
                                    yield {
                                        "event": "content",
                                        "data": {
                                            "id": str(getattr(message, 'id', '')),
                                            "step": step,
                                            "content": content_text,
                                            "role": "assistant"
                                        }
                                    }

                        # Handle ToolMessage (tool results)
                        elif step == "tools":
                            tool_content = message.content if hasattr(message, 'content') else str(message)
                            tool_name = message.name if hasattr(message, 'name') else 'unknown'
                            tool_call_id = message.tool_call_id if hasattr(message, 'tool_call_id') else ''

                            yield {
                                "event": "tool_result",
                                "data": {
                                    "id": tool_call_id,
                                    "step": step,
                                    "tool_name": tool_name,
                                    "result": tool_content,
                                    "status": "completed"
                                }
                            }

                    except Exception as e:
                        logger.error(f"Error processing step {step}: {str(e)}")
                        logger.exception(e)

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            logger.exception(e)
            yield {
                "event": "error",
                "data": {
                    "message": str(e)
                }
            }


