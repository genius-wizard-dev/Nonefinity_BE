from typing import List, Optional

from app.crud.base import BaseCRUD
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserCRUD(BaseCRUD[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, emails: List[str]) -> Optional[User]:
        return await self.model.find_one({"emails": {"$in": emails}})

    async def get_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        return await self.model.find_one(User.clerk_id == clerk_id)


user_crud = UserCRUD()
