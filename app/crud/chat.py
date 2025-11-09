from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.chat import ChatConfig, ChatSession, ChatMessage
from app.schemas.chat import ChatConfigCreate, ChatConfigUpdate, ChatSessionCreate, ChatMessageCreate
from bson import ObjectId


class ChatConfigCRUD(BaseCRUD[ChatConfig, ChatConfigCreate, ChatConfigUpdate]):
    def __init__(self):
        super().__init__(ChatConfig)

    async def get_by_name(self, name: str, owner_id: str) -> List[ChatConfig]:
        return await self.model.find(
            ChatConfig.name == name,
            ChatConfig.owner_id == owner_id
        ).to_list()

    async def delete_by_chat_config_id(self, chat_config_id: str) -> bool:
        # Delete the chat config
        await ChatConfig.find_one({"_id": ObjectId(chat_config_id)}).delete()

        # Find all sessions under this config
        sessions = await ChatSession.find(
            ChatSession.chat_config_id == chat_config_id
        ).to_list()

        # Delete messages and sessions
        for session in sessions:
            await ChatMessage.find(ChatMessage.session_id == session.id).delete()
            await ChatSession.find_one({"_id": ObjectId(session.id)}).delete()
        return True

    async def get_by_knowledge_store_id(self, knowledge_store_id: str, owner_id: str) -> List[ChatConfig]:
        return await self.list(
            filter_={"knowledge_store_id": str(knowledge_store_id), "owner_id": owner_id},
            include_deleted=False
        )

chat_config_crud = ChatConfigCRUD()

class ChatSessionCRUD(BaseCRUD[ChatSession, ChatSessionCreate, None]):
    def __init__(self):
        super().__init__(ChatSession)

    async def delete_by_chat_session_id(self, chat_session_id: str) -> bool:
        # Delete the chat session
        await ChatSession.find_one({"_id": ObjectId(chat_session_id)}).delete()
        # Delete all messages for this session
        await ChatMessage.find_all({"session_id": ObjectId(chat_session_id)}).delete()
        return True

    async def delete_by_chat_session_ids(self, chat_session_ids: List[str]) -> bool:
        """Delete multiple chat sessions and their messages"""
        # Convert all IDs to ObjectId
        object_ids = [ObjectId(session_id) for session_id in chat_session_ids]
        
        # Delete all chat sessions
        await ChatSession.find({"_id": {"$in": object_ids}}).delete()
        # Delete all messages for these sessions
        await ChatMessage.find({"session_id": {"$in": object_ids}}).delete()
        return True

    async def get_by_name(self, name: str, owner_id: str) -> Optional[ChatSession]:
        return await self.get_one(
            filter_={"name": name, "owner_id": owner_id},
            include_deleted=False
        )


chat_session_crud = ChatSessionCRUD()

class ChatMessageCRUD(BaseCRUD[ChatMessage, ChatMessageCreate, None]):
    def __init__(self):
        super().__init__(ChatMessage)

    async def delete_by_chat_session_id(self, chat_session_id: str) -> bool:
        await ChatMessage.find_all({"session_id": chat_session_id}).delete()
        return True

chat_message_crud = ChatMessageCRUD()
