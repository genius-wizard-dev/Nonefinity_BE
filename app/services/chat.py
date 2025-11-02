from typing import List, Any
import json

from app.crud import chat_config_crud, chat_session_crud, chat_message_crud, model_crud, credential_crud, user_crud, dataset_crud, knowledge_store_crud
from app.models.chat import ChatMessage
from app.schemas.chat import (
    ChatConfigCreate, ChatConfigUpdate, ChatConfigResponse, ChatConfigListResponse,
    ChatSessionCreate, ChatSessionResponse, ChatSessionListResponse,
    ChatMessageCreate, ChatMessageResponse, ChatMessageListResponse,
    SaveChatMessageRequest,
)
from langchain_core.tools.base import BaseTool
from app.models.chat import ChatConfig
from app.databases.qdrant import qdrant
from app.services.dataset_service import DatasetService
from app.core.exceptions import AppError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from app.utils import get_logger
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from app.agents.types import AgentContext
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.llms import LLMConfig, EmbeddingModelConfig
from app.agents.tools import dataset_tools, knowledge_tools
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.runnables.config import RunnableConfig
from app.services import provider_service, credential_service
from app.agents.middleware import NonfinityAgentMiddleware
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


    async def get_chat_config_by_id(self, owner_id: str, chat_config_id: str) -> ChatConfigResponse:
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

    async def get_list_chat_configs(self, owner_id: str, skip: int = 0, limit: int = 100) -> ChatConfigListResponse:
        """Get all chats for a user"""
        chat_configs = await self._chat_config_crud.list(owner_id=owner_id, skip=skip, limit=limit)
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
        chat_config = await self._chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)
        if not chat_config:
            raise AppError(message="Chat config not found", status_code=HTTP_404_NOT_FOUND)

        update_dict = chat_config_data.model_dump(exclude_unset=True)
        if 'name' in update_dict and update_dict['name'] != chat_config.name:
            existing_chat_config = await self._chat_config_crud.get_by_name(update_dict['name'], owner_id)
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
        chat_config = await self._chat_config_crud.get_by_id(id=chat_config_id, owner_id=owner_id)
        if not chat_config:
            raise AppError(message="Chat config not found", status_code=HTTP_404_NOT_FOUND)
        await self._chat_config_crud.delete_by_chat_config_id(chat_config_id)
        return True

    async def create_chat_session(self, owner_id: str, chat_session_data: ChatSessionCreate) -> ChatSessionResponse:
        """Create a new chat session"""
        if chat_session_data.name:
            existing_chat_session = await self._chat_session_crud.get_by_name(chat_session_data.name, owner_id)
            if existing_chat_session:
                raise AppError(message="Chat session with this name already exists", status_code=HTTP_400_BAD_REQUEST)
        chat_config = await self._chat_config_crud.get_by_id(id=chat_session_data.chat_config_id, owner_id=owner_id)
        if not chat_config:
            raise AppError(message="Chat config not found", status_code=HTTP_404_NOT_FOUND)

        chat_session = await self._chat_session_crud.create(chat_session_data, owner_id=owner_id)
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
        chat_session = await self._chat_session_crud.get_by_id(id=chat_session_id, owner_id=owner_id)
        if not chat_session:
            raise AppError(message="Chat session not found", status_code=HTTP_404_NOT_FOUND)
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
            raise AppError(message="Chat session not found", status_code=HTTP_404_NOT_FOUND)
        await self._chat_session_crud.delete_by_chat_session_id(chat_session_id)
        return True

    async def delete_chat_session_messages(self, owner_id: str, chat_session_id: str) -> bool:
        """Delete all messages for a chat session"""
        messages = await self._chat_message_crud.list(filter_={"session_id": chat_session_id}, owner_id=owner_id)
        if not messages:
            raise AppError(message="No messages found", status_code=HTTP_404_NOT_FOUND)
        await self._chat_message_crud.delete_by_chat_session_id(chat_session_id)
        return True

    async def create_chat_message(self, owner_id: str, chat_session_id: str, chat_message_data: ChatMessageCreate) -> ChatMessageResponse:
        """Create a new chat message"""
        # Ensure session_id is set in the data
        if chat_message_data.session_id != chat_session_id:
            chat_message_data = chat_message_data.model_copy(update={"session_id": chat_session_id})
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
        tools = dataset_tools if chat_config.dataset_ids else []
        tools += knowledge_tools if chat_config.knowledge_store_id else []
        return tools


    async def stream_agent_response(self, owner_id: str, chat_session_id: str, message: str):
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
            dataset_service = DatasetService(access_key=owner_id, secret_key=user.minio_secret_key) if chat_config.dataset_ids else None
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
                    # After schema, add a note for the AI about using '{{data á}}' for JSON data.
                    datasets_str += (
                        f"- {name}: {ds_desc}\n"
                        f"  Các cột và mô tả:\n"
                        f"{schema_str}\n"
                    )

            system_prompt = SYSTEM_PROMPT.format(datasets=datasets_str, tools=tools, instruction_prompt=chat_config.instruction_prompt)

            agent = create_agent(
                model=llm,
                tools=tools,
                middleware=[NonfinityAgentMiddleware()],
                context_schema=AgentContext,
                state_schema=AgentState,
                checkpointer=InMemorySaver(),
                system_prompt=system_prompt
            )
            context = AgentContext(user_id=owner_id, dataset_service=dataset_service, datasets=datasets, knowledge_store_collection_name=knowledge_store_collection_name, embedding_model=embedding_model, session_id=chat_session_id)

            messages_input = {"messages": [
              HumanMessage(content=message),
            ]}


            config = RunnableConfig(configurable={"thread_id": chat_session_id})
            async for chunk in agent.astream(input=messages_input, stream_mode="updates", config=config, context=context):
              logger.info(f"Chunk: {chunk}")
              for key, value in chunk.items():
                  msg = value["messages"][0]

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
