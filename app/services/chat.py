from typing import List
import json
import random
from bson import ObjectId
from app.crud import chat_config_crud, chat_session_crud, chat_message_crud, model_crud, credential_crud, user_crud, dataset_crud, knowledge_store_crud
from app.models.chat import ChatMessage
from app.schemas.chat import (
    ChatConfigCreate, ChatConfigUpdate, ChatConfigResponse, ChatConfigListResponse,
    ChatSessionCreate, ChatSessionResponse, ChatSessionListResponse,
    ChatMessageCreate, ChatMessageResponse, ChatMessageListResponse,
    SaveChatMessageRequest,
)
import pytz
from langchain_core.tools.base import BaseTool
from app.models.chat import ChatConfig
from app.services.dataset_service import DatasetService
from app.core.exceptions import AppError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from app.utils import get_logger
from datetime import datetime
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from app.services.intergrate_service import integration_service
from app.agents.types import AgentContext
from app.services.composio_service import composio_service
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.llms import LLMConfig, EmbeddingModelConfig
from app.agents.tools import dataset_tools, knowledge_tools
from langchain_core.messages import HumanMessage
from app.services.mcp_service import mcp_service
from langchain_core.runnables.config import RunnableConfig
from app.services import provider_service, credential_service
from app.agents.middleware import NonfinityAgentMiddleware, summary_middleware
logger = get_logger(__name__)


class ChatService:
    """Service for chat operations"""

    def __init__(self):
        self._chat_config_crud = chat_config_crud
        self._chat_session_crud = chat_session_crud
        self._chat_message_crud = chat_message_crud
        self._model_crud = model_crud
        self._credential_crud = credential_crud
        self._provider_service = provider_service
        self._user_crud = user_crud
        self._credential_service = credential_service
        self._dataset_crud = dataset_crud
        self._knowledge_store_crud = knowledge_store_crud

    def _create_id_alias(self, name: str) -> str:
        """Create an ID alias from normalized name + 6 random digits"""
        # Normalize name: lowercase, replace spaces with hyphens, remove special chars
        normalized_name = name.strip().lower().replace(' ', '-')
        # Remove special characters, keep only alphanumeric and hyphens
        normalized_name = ''.join(
            c for c in normalized_name if c.isalnum() or c == '-')
        # Remove consecutive hyphens
        normalized_name = '-'.join(filter(None, normalized_name.split('-')))
        # Generate 6 random digits
        random_part = random.randint(100000, 999999)
        return f"{normalized_name}-{random_part}"

    async def _ensure_id_alias(self, chat_config: ChatConfig) -> ChatConfig:
        """Ensure chat config has id_alias, generate if missing (for backward compatibility)"""
        if not chat_config.id_alias:
            chat_config.id_alias = self._create_id_alias(chat_config.name)
            await chat_config.save()
        return chat_config

    async def create_chat_config(self, owner_id: str, chat_config_data: ChatConfigCreate) -> ChatConfigResponse:
        """Create a new chat configuration  """
        # Check if chat name already exists for this owner
        existing_chat_config = await self._chat_config_crud.get_by_name(chat_config_data.name, owner_id)
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

        # Create ID alias (normalized name + 6 random digits, backend generated)
        id_alias = self._create_id_alias(chat_config_data.name)
        # Ensure id_alias is not in the create data, we'll add it manually
        create_data = chat_config_data.model_dump(exclude={"id_alias"})
        create_data["id_alias"] = id_alias

        # Convert None to empty list for dataset_ids (model requires List[str], not Optional)
        if create_data.get("dataset_ids") is None:
            create_data["dataset_ids"] = []

        # Convert None to empty list for mcp_ids (model requires List[str], not Optional)
        if create_data.get("mcp_ids") is None:
            create_data["mcp_ids"] = []

        # Convert None to empty dict for selected_tools (model requires Dict, not Optional)
        if create_data.get("selected_tools") is None:
            create_data["selected_tools"] = {}

        # Create chat
        chat_config = await self._chat_config_crud.create(create_data, owner_id=owner_id)
        # Ensure id_alias exists (should always exist for new records)
        chat_config = await self._ensure_id_alias(chat_config)
        # Check if config is being used by any sessions
        session_count = await self._chat_session_crud.count_sessions_by_config_id(
            str(chat_config.id), owner_id
        )
        is_used = session_count > 0

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
            id_alias=chat_config.id_alias,
            is_used=is_used,
            mcp_ids=chat_config.mcp_ids if chat_config.mcp_ids else None,
            selected_tools=chat_config.selected_tools if chat_config.selected_tools else None,
        )

    async def get_chat_config_by_id(self, owner_id: str, chat_config_id: str) -> ChatConfigResponse:
        """Get a specific chat by ID (supports both MongoDB ObjectId and id_alias)"""
        # Try to get by MongoDB ObjectId first
        chat_config = await self._chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)

        # If not found, try to get by id_alias (numeric string)
        if not chat_config:
            chat_config = await self._chat_config_crud.get_by_id_alias(id_alias=chat_config_id, owner_id=owner_id)

        if not chat_config:
            raise AppError(message="Chat config not found",
                           status_code=HTTP_404_NOT_FOUND)

        # Ensure id_alias exists (for backward compatibility with old records)
        chat_config = await self._ensure_id_alias(chat_config)

        # Check if config is being used by any sessions
        session_count = await self._chat_session_crud.count_sessions_by_config_id(
            str(chat_config.id), owner_id
        )
        is_used = session_count > 0

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
            id_alias=chat_config.id_alias,
            is_used=is_used,
            mcp_ids=chat_config.mcp_ids if chat_config.mcp_ids else None,
            selected_tools=chat_config.selected_tools if chat_config.selected_tools else None,
        )

    async def get_list_chat_configs(self, owner_id: str, skip: int = 0, limit: int = 100) -> ChatConfigListResponse:
        """Get all chats for a user"""
        chat_configs = await self._chat_config_crud.list(owner_id=owner_id, skip=skip, limit=limit)
        config_responses = []
        for config in chat_configs:
            # Ensure id_alias exists (for backward compatibility with old records)
            config = await self._ensure_id_alias(config)

            # Check if config is being used by any sessions
            session_count = await self._chat_session_crud.count_sessions_by_config_id(
                str(config.id), owner_id
            )
            is_used = session_count > 0

            config_responses.append(
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
                    id_alias=config.id_alias,
                    is_used=is_used,
                    mcp_ids=config.mcp_ids if config.mcp_ids else None,
                    selected_tools=config.selected_tools if config.selected_tools else None,
                )
            )
        return ChatConfigListResponse(
            chat_configs=config_responses,
            total=len(config_responses),
            skip=skip,
            limit=limit
        )

    async def update_chat_config(self, owner_id: str, chat_config_id: str, chat_config_data: ChatConfigUpdate) -> ChatConfigResponse:
        """Update a chat configuration (id_alias cannot be updated)"""
        # Try to get by MongoDB ObjectId first
        chat_config = await self._chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)

        # If not found, try to get by id_alias (numeric string)
        if not chat_config:
            chat_config = await self._chat_config_crud.get_by_id_alias(id_alias=chat_config_id, owner_id=owner_id)

        if not chat_config:
            raise AppError(message="Chat config not found",
                           status_code=HTTP_404_NOT_FOUND)

        # Ensure id_alias exists (for backward compatibility with old records)
        chat_config = await self._ensure_id_alias(chat_config)

        update_dict = chat_config_data.model_dump(exclude_unset=True)

        # Convert None to empty list for dataset_ids (model requires List[str], not Optional)
        if "dataset_ids" in update_dict and update_dict["dataset_ids"] is None:
            update_dict["dataset_ids"] = []

        if 'name' in update_dict and update_dict['name'] != chat_config.name:
            existing_chat_config = await self._chat_config_crud.get_by_name(update_dict['name'], owner_id)
            if existing_chat_config and str(existing_chat_config.id) != chat_config_id:
                raise AppError(
                    message="Chat config with this name already exists",
                    status_code=HTTP_400_BAD_REQUEST
                )

        if 'mcp_ids' in update_dict and update_dict['mcp_ids'] is None:
            update_dict['mcp_ids'] = []

        if 'selected_tools' in update_dict and update_dict['selected_tools'] is None:
            update_dict['selected_tools'] = {}

        # Validate configuration updates
        if "embedding_model_id" in update_dict or "knowledge_store_id" in update_dict:
            new_embedding_model_id = update_dict.get(
                "embedding_model_id", chat_config.embedding_model_id)
            new_knowledge_store_id = update_dict.get(
                "knowledge_store_id", chat_config.knowledge_store_id)

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
        # Check if config is being used by any sessions
        session_count = await self._chat_session_crud.count_sessions_by_config_id(
            str(chat_config.id), owner_id
        )
        is_used = session_count > 0

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
            id_alias=chat_config.id_alias,
            is_used=is_used,
            mcp_ids=chat_config.mcp_ids if chat_config.mcp_ids else None,
            selected_tools=chat_config.selected_tools if chat_config.selected_tools else None,
        )

    async def delete_chat_config(self, owner_id: str, chat_config_id: str) -> bool:
        """Delete a chat configuration (supports both MongoDB ObjectId and id_alias)"""
        # Try to get by MongoDB ObjectId first
        chat_config = await self._chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)

        # If not found, try to get by id_alias (numeric string)
        if not chat_config:
            chat_config = await self._chat_config_crud.get_by_id_alias(id_alias=chat_config_id, owner_id=owner_id)

        if not chat_config:
            raise AppError(message="Chat config not found",
                           status_code=HTTP_404_NOT_FOUND)

        # Ensure id_alias exists before deletion (for logging/audit purposes)
        chat_config = await self._ensure_id_alias(chat_config)

        # Check if config is being used by any sessions
        session_count = await self._chat_session_crud.count_sessions_by_config_id(
            str(chat_config.id), owner_id
        )
        if session_count > 0:
            raise AppError(
                message=f"Cannot delete chat config. It is being used by {session_count} session(s). Please delete all sessions first.",
                status_code=HTTP_400_BAD_REQUEST
            )

        # Use the actual MongoDB ID for deletion
        await self._chat_config_crud.delete_by_chat_config_id(str(chat_config.id))
        return True

    async def create_chat_session(self, owner_id: str, chat_session_data: ChatSessionCreate) -> ChatSessionResponse:
        """Create a new chat session"""
        # Resolve chat config first (supports both ObjectId and id_alias)
        chat_config = None
        if ObjectId.is_valid(chat_session_data.chat_config_id):
            chat_config = await self._chat_config_crud.get_by_id(id=chat_session_data.chat_config_id, owner_id=owner_id)

        # If not found (or invalid ObjectId), try to get by id_alias
        if not chat_config:
            chat_config = await self._chat_config_crud.get_by_id_alias(id_alias=chat_session_data.chat_config_id, owner_id=owner_id)

        if not chat_config:
            raise AppError(message="Chat config not found",
                           status_code=HTTP_404_NOT_FOUND)

        # Ensure id_alias exists (for backward compatibility with old records)
        chat_config = await self._ensure_id_alias(chat_config)

        # Update chat_config_id to the actual ObjectId string to ensure consistency
        chat_session_data.chat_config_id = str(chat_config.id)

        if chat_session_data.name:
            existing_chat_session = await self._chat_session_crud.get_by_name(chat_session_data.name, owner_id, chat_config_id=chat_session_data.chat_config_id)
            if existing_chat_session:
                raise AppError(
                    message="Chat session with this name already exists", status_code=HTTP_400_BAD_REQUEST)

        chat_session = await self._chat_session_crud.create(chat_session_data, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Failed to create chat session",
                           status_code=HTTP_400_BAD_REQUEST)

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
        chat_session = await self._chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Chat session not found",
                           status_code=HTTP_404_NOT_FOUND)
        messages = await self._chat_message_crud.list(filter_={"session_id": chat_session_id}, owner_id=owner_id, skip=skip, limit=limit)
        message_responses = []
        for message in messages:
            tools_value = message.tools
            if isinstance(tools_value, dict):
                tools_value = [tools_value]
            elif tools_value is not None and not isinstance(tools_value, list):
                tools_value = None

            message_responses.append(
                ChatMessageResponse(
                    id=str(message.id),
                    session_id=message.session_id,
                    role=message.role,
                    content=message.content,
                    tools=tools_value,
                    created_at=message.created_at,
                    updated_at=message.updated_at
                )
            )
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
        chat_sessions = await self._chat_session_crud.list(owner_id=owner_id, skip=skip, limit=limit)
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
        chat_session = await self._chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Chat session not found",
                           status_code=HTTP_404_NOT_FOUND)
        await self._chat_session_crud.delete_by_chat_session_id(chat_session_id)
        return True

    async def delete_chat_sessions(self, owner_id: str, session_ids: List[str]) -> int:
        """Delete multiple chat sessions"""
        deleted_count = await self._chat_session_crud.delete_by_ids(session_ids, owner_id)
        return deleted_count

    async def delete_chat_session_messages(self, owner_id: str, chat_session_id: str) -> bool:
        """Delete all messages for a chat session"""
        messages = await self._chat_message_crud.list(filter_={"session_id": chat_session_id}, owner_id=owner_id)
        if not messages:
            raise AppError(message="No messages found",
                           status_code=HTTP_404_NOT_FOUND)
        await self._chat_message_crud.delete_by_chat_session_id(chat_session_id)
        return True

    async def create_chat_message(self, owner_id: str, chat_session_id: str, chat_message_data: ChatMessageCreate) -> ChatMessageResponse:
        """Create a new chat message"""
        # Ensure session_id is set in the data
        if chat_message_data.session_id != chat_session_id:
            chat_message_data = chat_message_data.model_copy(
                update={"session_id": chat_session_id})
        chat_message = await self._chat_message_crud.create(chat_message_data, owner_id=owner_id)
        tools_value = chat_message.tools
        if isinstance(tools_value, dict):
            tools_value = [tools_value]
        elif tools_value is not None and not isinstance(tools_value, list):
            tools_value = None

        return ChatMessageResponse(
            id=str(chat_message.id),
            session_id=chat_message.session_id,
            role=chat_message.role,
            content=chat_message.content,
            tools=tools_value,
            created_at=chat_message.created_at,
            updated_at=chat_message.updated_at
        )

    async def save_conversation_batch(self, owner_id: str, session_id: str, messages: List[SaveChatMessageRequest]) -> bool:
        """Save a batch of messages representing complete conversation flow"""
        try:
            # Verify session exists
            chat_session = await self._chat_session_crud.get_by_id(id=session_id, owner_id=owner_id)
            if not chat_session:
                raise AppError(
                    message="Chat session not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            # Create messages from batch data
            for message_data in messages:
                content_raw = message_data.content
                content = content_raw if content_raw else ""

                chat_message_data = ChatMessageCreate(
                    session_id=session_id,
                    role=message_data.role,
                    content=content,
                    tools=message_data.tools,
                )
                await self._chat_message_crud.create(chat_message_data, owner_id=owner_id)

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

    async def _get_recent_messages(self, owner_id: str, chat_session_id: str) -> List[ChatMessage]:
        """Get recent messages for a chat session"""
        pass

    async def _setup_tools(self, chat_config: ChatConfig) -> List[BaseTool]:
        """Setup tools for a chat config"""
        # Use list() to create a copy, avoiding mutation of the original lists
        tools = list(dataset_tools) if chat_config.dataset_ids else []
        tools += list(knowledge_tools) if chat_config.knowledge_store_id else []

        # Parse selected_tools from new format: {integration_name: {tools: [tool_slug, ...]}}
        selected_tools_dict = chat_config.selected_tools if chat_config.selected_tools else {}
        all_tool_slugs = []
        print(f"selected_tools_dict: {selected_tools_dict}")
        for integration_name, tool_data in selected_tools_dict.items():
            if isinstance(tool_data, dict) and "tools" in tool_data:
                all_tool_slugs.extend(tool_data.get("tools", []))

        if all_tool_slugs:
            integration_tools = await composio_service.async_get_list_tools(all_tool_slugs, user_id=chat_config.owner_id)
            tools += integration_tools

        mcp_ids = chat_config.mcp_ids if chat_config.mcp_ids else []
        if mcp_ids:
            mcp_tools = await mcp_service.get_tools_by_mcp_ids(chat_config.owner_id, mcp_ids)
            tools += mcp_tools
        return tools

    async def stream_agent_response(self, owner_id: str, chat_session_id: str, message: str, timezone: str):
        """Stream agent response as async generator

        Creates a new agent instance for each request and loads the last 5 messages as history.

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

            # Get chat session
            chat_session = await self._chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
            if not chat_session:
                raise AppError(
                    message="Chat session not found",
                    status_code=HTTP_404_NOT_FOUND
                )

            # Get chat config
            chat_config = await self._chat_config_crud.get_by_id(id=chat_session.chat_config_id, owner_id=owner_id)
            if not chat_config:
                raise AppError(
                    message="Chat config not found",
                    status_code=HTTP_404_NOT_FOUND
                )
             # Ensure id_alias exists (for backward compatibility with old records)
            chat_config = await self._ensure_id_alias(chat_config)

            llm_config = await LLMConfig.from_model_id(
                owner_id=owner_id,
                model_id=chat_config.chat_model_id,
            )
            llm = llm_config.get_llm()
            embedding_model = None
            if chat_config.embedding_model_id:
                embedding_model_config = await EmbeddingModelConfig.from_model_id(
                    owner_id=owner_id,
                    embedding_model_id=chat_config.embedding_model_id,
                )
                embedding_model = embedding_model_config.get_embedding_model()

            tools = await self._setup_tools(chat_config)
            json_tools = [{"name": tool.name, "description": getattr(
                tool, "description", "")} for tool in tools]
            dataset_service = DatasetService(
                access_key=owner_id, secret_key=user.minio_secret_key) if chat_config.dataset_ids else None
            datasets = await self._dataset_crud.get_by_owner_and_ids(owner_id, chat_config.dataset_ids) if chat_config.dataset_ids else None
            knowledge_store_collection_name = None

            if chat_config.knowledge_store_id and embedding_model:
                knowledge_store_collection = await self._knowledge_store_crud.get_by_owner_and_id(owner_id, chat_config.knowledge_store_id)
                if not knowledge_store_collection:
                    raise AppError(
                        message="Knowledge store not found",
                        status_code=HTTP_404_NOT_FOUND
                    )
                knowledge_store_collection_name = knowledge_store_collection.collection_name

            def render_schema_field(field):
                return f"""  - {field['column_name']} ({field['column_type']}): {field.get('desc', '')}"""

            datasets_str = ""
            if datasets:
                for ds in datasets:
                    ds_desc = getattr(ds, "description", "") or ""
                    name = getattr(ds, "name", "") or ""
                    schema = getattr(ds, "data_schema", [])
                    schema_str_lines = []
                    for f in schema:
                        schema_str_lines.append(render_schema_field(f))
                    schema_str = "\n".join(schema_str_lines)
                    datasets_str += (
                        f"- {name}: {ds_desc}\n"
                        f"  Các cột và mô tả:\n"
                        f"{schema_str}\n"
                    )

            # Convert timezone string to timezone object
            tz = pytz.timezone(timezone) if timezone else pytz.UTC
            now = datetime.now(tz)
            offset_hours = now.utcoffset().total_seconds() / 3600
            GMT = f"GMT{offset_hours:+.0f}"

            system_prompt = SYSTEM_PROMPT.format(
                datasets=datasets_str,
                tools=json_tools,
                instruction_prompt=chat_config.instruction_prompt,
                current_time=now.strftime("%H:%M"),
                current_date=now.strftime("%Y-%m-%d"),
                timezone=timezone or "UTC",
                gmt=GMT
            )

            agent = create_agent(
                model=llm,
                tools=tools,
                middleware=[NonfinityAgentMiddleware(), summary_middleware],
                context_schema=AgentContext,
                state_schema=AgentState,
                checkpointer=InMemorySaver(),
                system_prompt=system_prompt
            )
            context = AgentContext(user_id=owner_id, dataset_service=dataset_service, datasets=datasets,
                                   knowledge_store_collection_name=knowledge_store_collection_name, embedding_model=embedding_model, session_id=chat_session_id)

            messages_input = {"messages": [
                HumanMessage(content=message),
            ]}

            config = RunnableConfig(
                configurable={"thread_id": chat_session_id})
            async for chunk in agent.astream(input=messages_input, stream_mode="updates", config=config, context=context):
                logger.debug(f"Received chunk: {chunk}")
                for key, value in chunk.items():
                    logger.debug(
                        f"Processing chunk key: {key}, value type: {type(value)}, value: {value}")

                    # Skip if value is None or doesn't have messages
                    if value is None:
                        logger.debug(
                            f"Skipping chunk key '{key}': value is None")
                        continue

                    if not isinstance(value, dict):
                        logger.debug(
                            f"Skipping chunk key '{key}': value is not a dict, type: {type(value)}")
                        continue

                    if "messages" not in value:
                        logger.debug(
                            f"Skipping chunk key '{key}': value dict doesn't have 'messages' key. Available keys: {list(value.keys())}")
                        continue

                    messages = value.get("messages", [])
                    if not messages or len(messages) == 0:
                        logger.debug(
                            f"Skipping chunk key '{key}': messages list is empty")
                        continue

                    logger.debug(
                        f"Processing message from chunk key '{key}': {messages[0]}")
                    msg = messages[0]
                    if "function_call" in msg.additional_kwargs:
                        fc = msg.additional_kwargs["function_call"]
                        yield {
                            "event": "tool_calls",
                            "data": json.dumps({
                                "name": fc["name"],
                                "arguments": json.loads(fc["arguments"]),
                            })
                        }

                    elif key == "tools":
                        yield {
                            "event": "tool_results",
                            "data": json.dumps({
                                "name": msg.name,
                                "result": msg.content,
                            })
                        }

                    elif key == "model":
                        content = msg.content
                        if isinstance(content, list):
                            content = "".join(
                                segment.get("text", "")
                                for segment in content
                                if isinstance(segment, dict) and segment.get("type") == "text"
                            )
                        yield {
                            "event": "ai_result",
                            "data": json.dumps({
                                "role": "assistant",
                                "content": content,
                            })
                        }

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


chat_service = ChatService()
