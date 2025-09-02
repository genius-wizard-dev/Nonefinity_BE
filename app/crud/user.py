from typing import Optional

from app.crud.base import BaseCRUD
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserCRUD(BaseCRUD[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> Optional[User]:
        if include_deleted:
            return await self.model.find_one(User.email == email)
        return await self.model.find_one(User.email == email)

    async def get_by_clerk_id(self, clerk_id: str, *, include_deleted: bool = False) -> Optional[User]:
        if include_deleted:
            return await self.model.find_one(User.clerk_id == clerk_id)
        return await self.model.find_one(User.clerk_id == clerk_id)
