from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.chat import ChatHistory
from app.schemas.chat import ChatMessageCreate


class ChatHistoryCRUD(BaseCRUD[ChatHistory, ChatMessageCreate, None]):
    def __init__(self):
        super().__init__(ChatHistory)

    async def create_message(self, chat_id: str, owner_id: str, role: str, content: str) -> ChatHistory:
        """Create a new message in chat history"""
        # Get the next message order
        last_message = await self.model.find(
            ChatHistory.chat_id == chat_id
        ).sort([("message_order", -1)]).limit(1).first()

        next_order = (last_message.message_order + 1) if last_message else 1

        # Create new message
        message_data = {
            "chat_id": chat_id,
            "owner_id": owner_id,
            "role": role,
            "content": content,
            "message_order": next_order
        }

        return await self.create(message_data)

    async def get_messages_by_chat(self, chat_id: str, skip: int = 0, limit: int = 100) -> List[ChatHistory]:
        """Get messages for a chat with pagination"""
        return await self.model.find(
            ChatHistory.chat_id == chat_id
        ).sort([("message_order", 1)]).skip(skip).limit(limit).to_list()

    async def get_messages_by_owner(self, chat_id: str, owner_id: str, skip: int = 0, limit: int = 100) -> List[ChatHistory]:
        """Get messages for a chat by owner with pagination"""
        return await self.model.find(
            ChatHistory.chat_id == chat_id,
            ChatHistory.owner_id == owner_id
        ).sort([("message_order", 1)]).skip(skip).limit(limit).to_list()

    async def count_messages(self, chat_id: str, owner_id: str) -> int:
        """Count messages in a chat by owner"""
        return await self.model.find(
            ChatHistory.chat_id == chat_id,
            ChatHistory.owner_id == owner_id
        ).count()

    async def clear_chat_history(self, chat_id: str, owner_id: str) -> bool:
        """Clear all messages for a chat"""
        result = await self.model.find(
            ChatHistory.chat_id == chat_id,
            ChatHistory.owner_id == owner_id
        ).delete()
        return result.deleted_count > 0

    async def delete_message(self, message_id: str, owner_id: str) -> bool:
        """Delete a specific message"""
        message = await self.get_by_id(message_id)
        if not message or message.owner_id != owner_id:
            return False

        await self.delete(message)
        return True


# Create instance
chat_history_crud = ChatHistoryCRUD()
