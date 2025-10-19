from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.chat import Chat
from app.schemas.chat import ChatCreate, ChatUpdate


class ChatCRUD(BaseCRUD[Chat, ChatCreate, ChatUpdate]):
    def __init__(self):
        super().__init__(Chat)

    async def get_by_name(self, name: str, owner_id: str) -> Optional[Chat]:
        """Get chat by name and owner ID"""
        return await self.get_one(
            filter_={"name": name, "owner_id": owner_id},
            include_deleted=False
        )

    async def create_with_owner(self, owner_id: str, obj_in: ChatCreate) -> Chat:
        """Create chat with owner"""
        data = obj_in.model_dump()
        data["owner_id"] = owner_id

        db_obj = Chat(**data)
        await db_obj.insert()
        return db_obj

    async def get_by_owner(self, owner_id: str, skip: int = 0, limit: int = 100) -> List[Chat]:
        """Get chats by owner ID with pagination"""
        return await self.list(
            filter_={"owner_id": owner_id},
            skip=skip,
            limit=limit,
            include_deleted=False
        )

    async def get_by_owner_and_id(self, owner_id: str, chat_id: str) -> Optional[Chat]:
        """Get chat by owner and ID"""
        chat = await self.get_by_id(chat_id, include_deleted=False)
        if chat and chat.owner_id == owner_id:
            return chat
        return None

    async def count_by_owner(self, owner_id: str) -> int:
        """Count chats by owner ID"""
        chats = await self.list(
            filter_={"owner_id": owner_id},
            include_deleted=False
        )
        return len(chats)


# Create instance
chat_crud = ChatCRUD()
