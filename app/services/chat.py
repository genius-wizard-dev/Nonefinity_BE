from typing import List, Optional, Dict, Any
import json
from uuid import UUID

from app.crud.chat import chat_config_crud, chat_session_crud, chat_message_crud
from app.models.chat import ChatConfig, ChatSession, ChatMessage
from app.schemas.chat import (
    ChatConfigCreate, ChatConfigUpdate, ChatConfigResponse, ChatConfigListResponse,
    ChatSessionCreate, ChatSessionResponse, ChatSessionListResponse,
    ChatMessageCreate, ChatMessageResponse, ChatMessageListResponse
)
from app.services.dataset_service import DatasetService
from app.core.exceptions import AppError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from app.utils import get_logger
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from app.agents.context import AgentContext
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.llms import LLMConfig
from app.agents.tools import dataset_tools
from app.crud.model import ModelCRUD
from app.crud.credential import CredentialCRUD
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.runnables.config import RunnableConfig

from app.services.provider_service import ProviderService
from app.crud.user import UserCRUD
from app.services.credential_service import CredentialService
from langgraph.types import Interrupt, Command
logger = get_logger(__name__)


def _convert_chat_message_to_langchain_message(chat_message: ChatMessage) -> BaseMessage:
    """Convert ChatMessage to LangChain BaseMessage"""
    role = chat_message.role.lower()
    content = chat_message.content or ""

    if role == "user":
        return HumanMessage(content=content)
    elif role == "assistant":
        return AIMessage(content=content)
    elif role == "system":
        return SystemMessage(content=content)
    elif role == "tool":
        # ToolMessage needs tool_call_id
        tool_call_id = chat_message.tools.get("name", "") if chat_message.tools else ""
        return ToolMessage(content=content, tool_call_id=tool_call_id)
    else:
        # Default to HumanMessage
        return HumanMessage(content=content)


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
            chat_model_id=chat_config.chat_model_id,
            embedding_model_id=chat_config.embedding_model_id,
            knowledge_store_id=chat_config.knowledge_store_id,
            dataset_ids=chat_config.dataset_ids if chat_config.dataset_ids else None,
            instruction_prompt=chat_config.instruction_prompt,
            created_at=chat_config.created_at,
            updated_at=chat_config.updated_at,
        )


    async def get_chat_config(self, owner_id: str, chat_config_id: str) -> ChatConfigResponse:
        """Get a specific chat by ID"""
        chat_config = await self.chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)
        if not chat_config:
            raise AppError(message="Chat config not found", status_code=HTTP_404_NOT_FOUND)

        return ChatConfigResponse(
            id=str(chat_config.id),
            name=chat_config.name,
            chat_model_id=chat_config.chat_model_id,
            embedding_model_id=chat_config.embedding_model_id,
            knowledge_store_id=chat_config.knowledge_store_id,
            dataset_ids=chat_config.dataset_ids if chat_config.dataset_ids else None,
            instruction_prompt=chat_config.instruction_prompt,
            created_at=chat_config.created_at,
            updated_at=chat_config.updated_at,
        )

    async def get_chat_configs(self, owner_id: str, skip: int = 0, limit: int = 100) -> ChatConfigListResponse:
        """Get all chats for a user"""
        chat_configs = await self.chat_config_crud.list(owner_id=owner_id, skip=skip, limit=limit)
        config_responses = [
            ChatConfigResponse(
                id=str(config.id),
                name=config.name,
                chat_model_id=config.chat_model_id,
                embedding_model_id=config.embedding_model_id,
                knowledge_store_id=config.knowledge_store_id,
                dataset_ids=config.dataset_ids if config.dataset_ids else None,
                instruction_prompt=config.instruction_prompt,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )
            for config in chat_configs
        ]
        return ChatConfigListResponse(
            chat_configs=config_responses,
            total=len(config_responses),
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
            chat_model_id=chat_config.chat_model_id,
            embedding_model_id=chat_config.embedding_model_id,
            knowledge_store_id=chat_config.knowledge_store_id,
            dataset_ids=chat_config.dataset_ids if chat_config.dataset_ids else None,
            instruction_prompt=chat_config.instruction_prompt,
            created_at=chat_config.created_at,
            updated_at=chat_config.updated_at,
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
        if chat_session_data.name:
            existing_chat_session = await self.chat_session_crud.get_by_name(chat_session_data.name, owner_id)
            if existing_chat_session:
                raise AppError(message="Chat session with this name already exists", status_code=HTTP_400_BAD_REQUEST)
        chat_config = await self.chat_config_crud.get_by_id(id=chat_session_data.chat_config_id, owner_id=owner_id)
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

        chat_session = await self.chat_session_crud.create(chat_session_data, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Failed to create chat session", status_code=HTTP_400_BAD_REQUEST)

        return ChatSessionResponse(
            id=str(chat_session.id),
            chat_config_id=chat_session.chat_config_id,
            name=chat_session.name,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            messages=ChatMessageListResponse(
                chat_messages=[],
                total=0,
                skip=0,
                limit=100
            )
        )

    async def get_chat_session(self, owner_id: str, chat_session_id: str, skip: int = 0, limit: int = 100) -> ChatSessionResponse:
        """Get a specific chat session"""
        chat_session = await self.chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Chat session not found", status_code=HTTP_404_NOT_FOUND)
        messages = await self.chat_message_crud.list(filter_={"session_id": chat_session_id}, owner_id=owner_id, skip=skip, limit=limit)
        message_responses = [
            ChatMessageResponse(
                id=str(message.id),
                session_id=message.session_id,
                role=message.role,
                content=message.content,
                models=message.models,
                tools=message.tools,
                interrupt=message.interrupt,
                created_at=message.created_at,
                updated_at=message.updated_at
            )
            for message in messages
        ]
        return ChatSessionResponse(
            id=str(chat_session.id),
            chat_config_id=chat_session.chat_config_id,
            name=chat_session.name,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            messages=ChatMessageListResponse(
                chat_messages=message_responses,
                total=len(message_responses),
                skip=skip,
                limit=limit
            )
        )

    async def get_chat_sessions(self, owner_id: str, skip: int = 0, limit: int = 100) -> ChatSessionListResponse:
        """Get all chat sessions for a user"""
        chat_sessions = await self.chat_session_crud.list(owner_id=owner_id, skip=skip, limit=limit)
        session_responses = [
            ChatSessionResponse(
                id=str(session.id),
                chat_config_id=session.chat_config_id,
                name=session.name,
                created_at=session.created_at,
                updated_at=session.updated_at,
                messages=ChatMessageListResponse(
                    chat_messages=[],
                    total=0,
                    skip=0,
                    limit=100
                )
            )
            for session in chat_sessions
        ]
        return ChatSessionListResponse(
            chat_sessions=session_responses,
            total=len(session_responses),
            skip=skip,
            limit=limit
        )

    async def delete_chat_session(self, owner_id: str, chat_session_id: str) -> bool:
        """Delete a chat session"""
        chat_session = await self.chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Chat session not found", status_code=HTTP_404_NOT_FOUND)
        await self.chat_session_crud.delete_by_chat_session_id(chat_session_id)
        return True

    async def delete_chat_session_messages(self, owner_id: str, chat_session_id: str) -> bool:
        """Delete all messages for a chat session"""
        messages = await self.chat_message_crud.list(filter_={"session_id": chat_session_id}, owner_id=owner_id)
        if not messages:
            raise AppError(message="No messages found", status_code=HTTP_404_NOT_FOUND)
        await self.chat_message_crud.delete_by_chat_session_id(chat_session_id)
        return True

    async def create_chat_message(self, owner_id: str, chat_session_id: str, chat_message_data: ChatMessageCreate) -> ChatMessageResponse:
        """Create a new chat message"""
        # Ensure session_id is set in the data
        if chat_message_data.session_id != chat_session_id:
            chat_message_data = chat_message_data.model_copy(update={"session_id": chat_session_id})
        chat_message = await self.chat_message_crud.create(chat_message_data, owner_id=owner_id)
        return ChatMessageResponse(
            id=str(chat_message.id),
            session_id=chat_message.session_id,
            role=chat_message.role,
            content=chat_message.content,
            models=chat_message.models,
            tools=chat_message.tools,
            interrupt=chat_message.interrupt,
            created_at=chat_message.created_at,
            updated_at=chat_message.updated_at
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
                content_raw = message_data.get('content', '')

                # Convert content to string if it's not already
                if isinstance(content_raw, list):
                  # Extract text from list of dicts like [{"type": "text", "text": "..."}]
                  content = ""
                  for item in content_raw:
                    if isinstance(item, dict):
                      if item.get("type") == "text":
                        content += item.get("text", "")
                      else:
                        content += str(item)
                    else:
                      content += str(item)
                elif isinstance(content_raw, str):
                  content = content_raw
                else:
                  content = str(content_raw) if content_raw else ""

                chat_message_data = ChatMessageCreate(
                    session_id=session_id,
                    role=message_data.get('role', 'user'),
                    content=content,
                    models=message_data.get('models', {}),
                    tools=message_data.get('tools', {}),
                    interrupt=message_data.get('interrupt', {})
                )
                await self.chat_message_crud.create(chat_message_data, owner_id=owner_id)

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

        Creates a new agent instance for each request and loads the last 5 messages as history.

        Args:
            owner_id: User ID
            chat_session_id: Chat session ID
            message: User message
        """
        logger.info(f"🚀 Starting stream_agent_response - session_id: {chat_session_id}, owner_id: {owner_id}, message_preview: {message[:100]}")
        try:
            user = await self._user_crud.get_by_id(owner_id)
            if not user:
                raise AppError(
                    message="User not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            logger.info(f"✅ User found: {owner_id}")

            # Get chat session
            chat_session = await self.chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
            if not chat_session:
                raise AppError(
                    message="Chat session not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            logger.info(f"✅ Chat session found: {chat_session_id}, config_id: {chat_session.chat_config_id}")

            # Get chat config
            chat_config = await self.chat_config_crud.get_by_id(id=chat_session.chat_config_id, owner_id=owner_id)
            if not chat_config:
                raise AppError(
                    message="Chat config not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            logger.info(f"✅ Chat config found: model_id={chat_config.chat_model_id}, dataset_ids={chat_config.dataset_ids}")

            # Get model and credential info
            model = await self._model_crud.get_by_id(id=chat_config.chat_model_id, owner_id=owner_id)
            if not model:
                raise AppError(
                    message="Model not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            logger.info(f"✅ Model found: {model.model}, credential_id: {model.credential_id}")

            credential = await self._credential_crud.get_by_id(id=model.credential_id, owner_id=owner_id)
            if not credential:
                raise AppError(
                    message="Credential not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            logger.info(f"✅ Credential found: provider_id={credential.provider_id}")

            provider = await self._provider_service.get_provider_by_id(credential.provider_id)
            if not provider:
                raise AppError(
                    message="Provider not found",
                    status_code=HTTP_404_NOT_FOUND
                )
            logger.info(f"✅ Provider found: {provider.provider}")

            # Prepare LLM config
            api_key = self._credential_service._decrypt_api_key(credential.api_key)
            base_url = credential.base_url if credential.base_url else None
            llm_config = LLMConfig(model=model.model, provider=provider.provider, api_key=api_key, base_url=base_url)
            logger.info(f"✅ LLM config created: model={model.model}, provider={provider.provider}")

            # Prepare tools
            tools = dataset_tools if chat_config.dataset_ids else []
            logger.info(f"✅ Tools prepared: {len(tools)} tools")

            # Get last 5 messages for history (newest first, then reverse to oldest first)
            # Query messages sorted by created_at descending to get most recent ones
            recent_messages = await self.chat_message_crud.model.find(
                {"session_id": chat_session_id, "owner_id": owner_id}
            ).sort("-created_at").limit(5).to_list()
            # Reverse to get oldest first (for proper conversation flow)
            recent_messages.reverse()
            logger.info(f"✅ Found {len(recent_messages)} recent messages for history")

            # Convert ChatMessage to LangChain messages
            history_messages = [_convert_chat_message_to_langchain_message(msg) for msg in recent_messages]
            logger.info(f"✅ Converted {len(history_messages)} messages to LangChain format")

            # Add new user message
            new_user_message = HumanMessage(content=message)
            all_messages = history_messages + [new_user_message]
            logger.info(f"✅ Total messages: {len(all_messages)} (history: {len(history_messages)}, new: 1)")

            dataset_service = DatasetService(access_key=owner_id, secret_key=user.minio_secret_key)
            agent = create_agent(
                model=llm_config.get_model(),
                tools=tools,
                middleware=[],
                context_schema=AgentContext,
                state_schema=AgentState,
                checkpointer=InMemorySaver(),
                system_prompt=SYSTEM_PROMPT
            )
            logger.info(f"✅ Agent created successfully")

            # Prepare input with message history
            messages_input = {"messages": all_messages}
            config = RunnableConfig(configurable={"thread_id": chat_session_id})
            logger.info(f"🔄 Starting agent stream with thread_id: {chat_session_id}")

            chunk_count = 0
            accumulated_model_content = ""
            last_model_content = ""

            for chunk in agent.stream(input=messages_input, stream_mode="updates", config=config, context=AgentContext(user_id=owner_id, dataset_service=dataset_service)):
                chunk_count += 1
                logger.debug(f"📦 Received chunk #{chunk_count}, keys: {list(chunk.keys())}")
                for key, value in chunk.items():
                    logger.debug(f"  🔍 Processing key: {key}, value_type: {type(value)}")
                    if key == "tools":
                      if type(value) == dict and "messages" in value:
                        msg_dict = value["messages"][0].model_dump()
                        tool_name = msg_dict.get("name", "")
                        tool_content_raw = msg_dict.get("content", "")

                        # Convert tool content to string
                        if isinstance(tool_content_raw, list):
                          tool_content = ""
                          for item in tool_content_raw:
                            if isinstance(item, dict) and item.get("type") == "text":
                              tool_content += item.get("text", "")
                            else:
                              tool_content += str(item)
                        elif isinstance(tool_content_raw, str):
                          tool_content = tool_content_raw
                        else:
                          tool_content = str(tool_content_raw) if tool_content_raw else ""

                        logger.info(f"📤 Yielding tool_result event: {tool_name}")
                        yield {
                                "event": "tool_result",
                                "data": {
                                    "role": "tool_result",
                                    "content": tool_content,
                                    "name": tool_name,
                                }
                            }
                    elif key == "model":
                      if type(value) == dict and "messages" in value:
                        msg_dict = value["messages"][0].model_dump()
                        tool_calls = msg_dict.get("tool_calls", [])
                        content_raw = msg_dict.get("content", "")

                        # Convert content to string if it's a list (LangChain format)
                        if isinstance(content_raw, list):
                          # Extract text from list of dicts like [{"type": "text", "text": "..."}]
                          content = ""
                          for item in content_raw:
                            if isinstance(item, dict):
                              if item.get("type") == "text":
                                content += item.get("text", "")
                              else:
                                content += str(item)
                            else:
                              content += str(item)
                        elif isinstance(content_raw, str):
                          content = content_raw
                        else:
                          content = str(content_raw) if content_raw else ""

                        logger.debug(f"  Model message - content_len: {len(content)}, tool_calls: {len(tool_calls) if tool_calls else 0}")

                        # Handle tool calls first
                        if tool_calls:
                          tools_list = []
                          for tool_call in tool_calls:
                            tools_list.append({
                              "name": tool_call.get("name", ""),
                              "args": tool_call.get("args", {}),
                              "id": tool_call.get("id", ""),
                            })
                          logger.info(f"📤 Yielding tool_calls event: {len(tool_calls)} tools")
                          yield {
                              "event": "tool_calls",
                              "data": {
                                  "role": "tool_calls",
                                  "tools": tools_list,
                                }
                          }
                          # Reset accumulated content when tool calls happen
                          accumulated_model_content = ""
                          last_model_content = ""

                        # Handle streaming content - detect incremental updates
                        elif content:
                          # Check if this is incremental content
                          if content.startswith(last_model_content) and len(content) > len(last_model_content):
                            # Incremental update - send only delta
                            delta = content[len(last_model_content):]
                            accumulated_model_content += delta
                            last_model_content = content
                            logger.debug(f"📤 Streaming delta: {len(delta)} chars (total: {len(accumulated_model_content)})")
                            yield {
                                "event": "ai_result",
                                "data": {
                                    "role": "ai_result",
                                    "content": delta,
                                    "is_delta": True,
                                }
                            }
                          elif content != last_model_content:
                            # New or replacement content
                            if last_model_content and not content.startswith(last_model_content):
                              # Full replacement
                              accumulated_model_content = content
                            else:
                              accumulated_model_content += content
                            last_model_content = content
                            logger.info(f"📤 Yielding ai_result event with content: {len(content)} chars")
                            yield {
                                "event": "ai_result",
                                "data": {
                                    "role": "ai_result",
                                    "content": content,
                                    "is_delta": False,
                                }
                            }

            logger.info(f"✅ Stream completed. Total chunks: {chunk_count}")


        except AppError as e:
            logger.error(f"Stream error: {e.message}")
            yield {
                "event": "error",
                "data": {
                    "message": e.message,
                    "status_code": e.status_code
                }
            }
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            logger.exception(e)
            yield {
                "event": "error",
                "data": {
                    "message": str(e)
                }
            }



