from typing import List, Optional

from app.crud.chat import chat_crud
from app.crud.chat_history import chat_history_crud
from app.schemas.chat import (
    ChatCreate, ChatUpdate, ChatResponse, ChatListResponse,
    ChatMessageCreate, ChatMessageResponse
)
from app.core.exceptions import AppError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from app.utils import get_logger
from app.agents.main import get_agent
from app.agents.llms import LLMConfig
from app.agents.tools import dataset_tools
from app.crud.model import ModelCRUD
from app.crud.credential import CredentialCRUD
from langchain_core.messages import HumanMessage
from langchain.messages import HumanMessage
from langchain_core.runnables.config import RunnableConfig
import uuid
from app.agents.context import AgentContext
from app.services.dataset_service import DatasetService
from app.services.provider_service import ProviderService
from app.crud.user import UserCRUD
from app.services.credential_service import CredentialService
from langgraph.types import Interrupt
logger = get_logger(__name__)


class ChatService:
    """Service for chat operations"""

    def __init__(self):
        self.crud = chat_crud
        self.history_crud = chat_history_crud
        self._model_crud = ModelCRUD()
        self._credential_crud = CredentialCRUD()
        self._provider_service = ProviderService()
        self._user_crud = UserCRUD()
        self._credential_service = CredentialService()



    async def create_chat(self, owner_id: str, chat_data: ChatCreate) -> ChatResponse:
        """Create a new chat"""
        try:
            # Check if chat name already exists for this owner
            existing_chat = await self.crud.get_by_name(chat_data.name, owner_id)
            if existing_chat:
                raise AppError(
                    message="Chat with this name already exists",
                    status_code=HTTP_400_BAD_REQUEST
                )

            # Validate configuration
            if chat_data.embedding_model_id and not chat_data.knowledge_store_id:
                raise AppError(
                    message="Knowledge store ID is required when embedding model is provided",
                    status_code=HTTP_400_BAD_REQUEST
                )

            if chat_data.knowledge_store_id and not chat_data.embedding_model_id:
                raise AppError(
                    message="Embedding model ID is required when knowledge store is provided",
                    status_code=HTTP_400_BAD_REQUEST
                )

            # Create chat
            chat = await self.crud.create_with_owner(owner_id, chat_data)

            # Convert to response
            return self._to_response(chat)

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error creating chat for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error creating chat: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    async def get_chat(self, owner_id: str, chat_id: str) -> ChatResponse:
        """Get a specific chat by ID"""
        try:
            chat = await self.crud.get_by_owner_and_id(owner_id, chat_id)
            if not chat:
                raise AppError(
                    message="Chat not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            return self._to_response(chat)

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error getting chat {chat_id} for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error getting chat: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    async def get_chats(self, owner_id: str, skip: int = 0, limit: int = 100) -> List[ChatListResponse]:
        """Get all chats for a user"""
        try:
            chats = await self.crud.get_by_owner(owner_id, skip, limit)
            return [
                ChatListResponse(
                    id=str(chat.id),
                    name=chat.name,
                    owner_id=chat.owner_id,
                    chat_model_id=chat.chat_model_id,
                    embedding_model_id=chat.embedding_model_id,
                    knowledge_store_id=chat.knowledge_store_id,
                    dataset_ids=chat.dataset_ids if chat.dataset_ids else [],
                    message_count=chat.message_count,
                    created_at=chat.created_at,
                    updated_at=chat.updated_at
                )
                for chat in chats
            ]
        except Exception as e:
            logger.error(f"Error getting chats for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error getting chats: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    async def update_chat(self, owner_id: str, chat_id: str, chat_data: ChatUpdate) -> ChatResponse:
        """Update a chat"""
        try:
            chat = await self.crud.get_by_owner_and_id(owner_id, chat_id)
            if not chat:
                raise AppError(
                    message="Chat not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            # Check if new name conflicts with existing chat
            update_dict = chat_data.model_dump(exclude_unset=True)
            if 'name' in update_dict and update_dict['name'] != chat.name:
                existing_chat = await self.crud.get_by_name(update_dict['name'], owner_id)
                if existing_chat and str(existing_chat.id) != chat_id:
                    raise AppError(
                        message="Chat with this name already exists",
                        status_code=HTTP_400_BAD_REQUEST
                    )

            # Validate configuration updates
            if "embedding_model_id" in update_dict or "knowledge_store_id" in update_dict:
                new_embedding_model_id = update_dict.get("embedding_model_id", chat.embedding_model_id)
                new_knowledge_store_id = update_dict.get("knowledge_store_id", chat.knowledge_store_id)

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
                chat.embedding_model_id = update_dict['embedding_model_id']
            if 'knowledge_store_id' in update_dict:
                chat.knowledge_store_id = update_dict['knowledge_store_id']

            # Update other fields normally
            for key, value in update_dict.items():
                if key not in ['embedding_model_id', 'knowledge_store_id'] and value is not None:
                    setattr(chat, key, value)

            # Save the chat object directly to handle None values
            await chat.save()
            return self._to_response(chat)

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error updating chat {chat_id} for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error updating chat: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    async def delete_chat(self, owner_id: str, chat_id: str) -> bool:
        """Delete a chat and its history"""
        try:
            chat = await self.crud.get_by_owner_and_id(owner_id, chat_id)
            if not chat:
                raise AppError(
                    message="Chat not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            # Delete chat history first
            await self.history_crud.clear_chat_history(chat_id, owner_id)

            # Delete chat
            await self.crud.delete(chat)
            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error deleting chat {chat_id} for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error deleting chat: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    async def count_chats(self, owner_id: str) -> int:
        """Count total chats for a user"""
        try:
            return await self.crud.count_by_owner(owner_id)
        except Exception as e:
            logger.error(f"Error counting chats for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error counting chats: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    # Chat message operations
    async def add_message(self, owner_id: str, chat_id: str, message_data: ChatMessageCreate) -> ChatMessageResponse:
        """Add a message to chat history"""
        try:
            chat = await self.crud.get_by_owner_and_id(owner_id, chat_id)
            if not chat:
                raise AppError(
                    message="Chat not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            # Add message to chat history
            history_message = await self.history_crud.create_message(
                chat_id, owner_id, message_data.role, message_data.content
            )

            # Update message count in chat
            chat.message_count += 1
            await chat.save()

            return ChatMessageResponse(
                id=str(history_message.id),
                chat_id=str(history_message.chat_id),
                role=history_message.role,
                content=history_message.content,
                message_order=history_message.message_order,
                created_at=history_message.created_at
            )

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error adding message to chat {chat_id} for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error adding message: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    async def get_messages(self, owner_id: str, chat_id: str, skip: int = 0, limit: int = 100) -> List[ChatMessageResponse]:
        """Get chat messages"""
        try:
            chat = await self.crud.get_by_owner_and_id(owner_id, chat_id)
            if not chat:
                raise AppError(
                    message="Chat not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            messages = await self.history_crud.get_messages_by_owner(chat_id, owner_id, skip, limit)
            return [
                ChatMessageResponse(
                    id=str(msg.id),
                    chat_id=str(msg.chat_id),
                    role=msg.role,
                    content=msg.content,
                    message_order=msg.message_order,
                    created_at=msg.created_at
                )
                for msg in messages
            ]

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error getting messages for chat {chat_id} for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error getting messages: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    async def clear_history(self, owner_id: str, chat_id: str) -> ChatResponse:
        """Clear chat history"""
        try:
            chat = await self.crud.get_by_owner_and_id(owner_id, chat_id)
            if not chat:
                raise AppError(
                    message="Chat not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            # Clear history from separate collection
            success = await self.history_crud.clear_chat_history(chat_id, owner_id)

            if success:
                # Update message count in chat
                chat.message_count = 0
                await chat.save()

            # Return updated chat data
            return self._to_response(chat)

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error clearing history for chat {chat_id} for user {owner_id}: {str(e)}")
            raise AppError(
                message=f"Error clearing history: {str(e)}",
                status_code=HTTP_400_BAD_REQUEST
            )

    def _to_response(self, chat) -> ChatResponse:
        """Convert chat model to response schema"""
        return ChatResponse(
            id=str(chat.id),
            name=chat.name,
            owner_id=chat.owner_id,
            chat_model_id=chat.chat_model_id,
            embedding_model_id=chat.embedding_model_id,
            temperature=chat.temperature,
            max_tokens=chat.max_tokens,
            top_p=chat.top_p,
            dataset_ids=chat.dataset_ids,
            knowledge_store_id=chat.knowledge_store_id,
            instruction_prompt=chat.instruction_prompt,
            message_count=chat.message_count,
            created_at=chat.created_at,
            updated_at=chat.updated_at
        )

    async def stream_agent_response(self, owner_id: str, chat_id: str, question: str):
        """Stream agent response as async generator"""
        try:
            user = await self._user_crud.get_by_id(owner_id)
            if not user:
                raise AppError(
                    message="User not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            chat = await self.crud.get_by_owner_and_id(owner_id, chat_id)
            if not chat:
                raise AppError(
                    message="Chat not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            dataset_service = DatasetService(access_key=str(user.id), secret_key=str(user.minio_secret_key))
            context = AgentContext(user_id=owner_id, dataset_service=dataset_service)
            model = await self._model_crud.get_by_owner_and_id(owner_id, chat.chat_model_id)
            if not model:
                raise AppError(
                    message="Model not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            credential = await self._credential_crud.get_by_owner_and_id(owner_id, model.credential_id)
            if not credential:
                raise AppError(
                    message="Credential not found",
                    status_code=HTTP_404_NOT_FOUND
                )


            api_key = self._credential_service._decrypt_api_key(credential.api_key)
            base_url = credential.base_url if credential.base_url else None
            provider = await self._provider_service.get_provider_by_id(credential.provider_id)
            if not provider:
                raise AppError(
                    message="Provider not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            llm_config = LLMConfig(model=model.model, provider=provider.provider, api_key=api_key, base_url=base_url)
            if chat.dataset_ids:
                tools = dataset_tools
            else:
                tools = []
            agent = get_agent(tools, llm_config, [], context)
            config = RunnableConfig(configurable={"thread_id": chat_id})
            query = HumanMessage(content=question)
            messages = {
                "messages": [query]
            }


            # Stream chunks from agent
            for chunk in agent.stream(messages, config=config, stream_mode="updates"):
                for step, data in chunk.items():
                    # Handle regular message updates
                    if not step == "__interrupt__" and not step == "HumanInTheLoopMiddleware.after_model":
                        try:
                            blocks = data['messages'][-1].content_blocks
                            content_type = blocks[0]['type']
                            if content_type == "text":
                              content_text = blocks[0]['text']
                              yield {
                                "id": str(data.id),
                                "type": step,
                                "content": content_text,
                                "type": content_type,
                            }
                            elif content_type == "tool_call":
                              yield {
                                "id": str(data.id),
                                "type": step,
                                "tool": blocks[0]['tool_call']['name'],
                                "status": "pending",
                                "args": blocks[0]['tool_call']['args'],
                                "description": blocks[0]['tool_call']['description'],
                              }
                        except Exception as e:
                          logger.error(f"Error processing step {step}: {str(e)}")
                          pass
                    if step == "__interrupt__":
                        if isinstance(data, tuple) and isinstance(data[0], Interrupt):
                            interrupt_value = data[0].value
                            action_requests = interrupt_value.get('action_requests', [])
                            review_configs = interrupt_value.get('review_configs', [])
                            interrupt_id = data[0].id
                            for action in action_requests:
                                yield {
                                    "id": str(interrupt_id),
                                    "type": step,
                                    "action_name": action.get('name', review_configs.get('action_name', 'unknown')),
                                    "allowed_decisions": review_configs.get('allowed_decisions', []),
                          }
        except AppError:
            raise
        except Exception as e:
            yield {
                "type": "error",
                "message": str(e)
            }

