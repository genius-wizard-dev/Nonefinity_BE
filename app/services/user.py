from typing import Optional

from app.crud.user import UserCRUD
from app.schemas.user import UserCreate, UserResponse, UserUpdate


class UserService:
    def __init__(self, crud: Optional[UserCRUD] = None):
        self.crud = crud or UserCRUD()
        
    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[UserResponse]:
        user = await self.crud.get_by_clerk_id(clerk_id)
        if not user:
            return None
        return UserResponse(
            clerk_id=user.clerk_id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            has_image=user.has_image,
            profile_image=user.profile_image,
            banned=user.banned,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_oauth=user.is_oauth,
            oauth_provider=user.oauth_provider,
        )
        
    async def create_user(self, payload: UserCreate) -> UserResponse:
        exists = await self.crud.get_by_email(payload.email)
        if exists:
            raise ValueError("Email already registered")
        
        user = await self.crud.create(payload)
        return UserResponse(
            clerk_id=user.clerk_id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            has_image=user.has_image,
            profile_image=user.profile_image,
            banned=user.banned,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_oauth=user.is_oauth,
            oauth_provider=user.oauth_provider,
        )
        
    async def update_user(self, clerk_id: str, payload: UserUpdate) -> UserResponse:
        user = await self.crud.get_by_clerk_id(clerk_id)
        if not user:
            raise ValueError("User not found")
        
        user = await self.crud.update(user, payload)
        return UserResponse(
            clerk_id=user.clerk_id,
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            has_image=user.has_image,
            profile_image=user.profile_image,
            banned=user.banned,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_oauth=user.is_oauth,
            oauth_provider=user.oauth_provider,
        )
        
    async def delete_user(self, clerk_id: str) -> None:
        user = await self.crud.get_by_clerk_id(clerk_id)
        if not user:
            return
        await self.crud.delete(user, False)
