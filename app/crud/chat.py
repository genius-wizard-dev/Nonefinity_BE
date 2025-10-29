from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.chat import ChatConfig, ChatSession, ChatMessage
from app.schemas.chat import ChatConfigCreate, ChatConfigUpdate, ChatSessionCreate, ChatMessageCreate
from app.agents.main import agent_manager


class ChatConfigCRUD(BaseCRUD[ChatConfig, ChatConfigCreate, ChatConfigUpdate]):
    def __init__(self):
        super().__init__(ChatConfig)

    async def get_by_name(self, name: str, owner_id: str) -> List[ChatConfig]:
        return await self.model.find(
            ChatConfig.name == name,
            ChatConfig.owner_id == owner_id
        ).to_list()

    async def delete_by_chat_config_id(self, chat_config_id: str) -> bool:
        await ChatConfig.find_one({"_id": chat_config_id}).delete()
        chat_session_ids = await ChatSession.find_all({"chat_config_id": chat_config_id}).to_list()
        for chat_session_id in chat_session_ids:
            await ChatMessage.find_all({"session_id": chat_session_id.id}).delete()
            await ChatSession.find_one({"_id": chat_session_id.id}).delete()
            await agent_manager.remove_agent(str(chat_session_id.id))
        return True

chat_config_crud = ChatConfigCRUD()

class ChatSessionCRUD(BaseCRUD[ChatSession, ChatSessionCreate, None]):
    def __init__(self):
        super().__init__(ChatSession)

    async def delete_by_chat_session_id(self, chat_session_id: str) -> bool:
        await ChatSession.find_one({"_id": chat_session_id}).delete()
        await ChatMessage.find_all({"session_id": chat_session_id}).delete()
        await agent_manager.remove_agent(chat_session_id)
        return True


chat_session_crud = ChatSessionCRUD()

class ChatMessageCRUD(BaseCRUD[ChatMessage, ChatMessageCreate, None]):
    def __init__(self):
        super().__init__(ChatMessage)

    async def delete_by_chat_session_id(self, chat_session_id: str) -> bool:
        await ChatMessage.find_all({"session_id": chat_session_id}).delete()
        return True

chat_message_crud = ChatMessageCRUD()
