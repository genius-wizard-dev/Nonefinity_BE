from typing import Optional

from app.crud.user import UserCRUD
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.minio_service import MinIOService
from app.utils import generate_secret_key
from app.utils import get_logger
from clerk_backend_api import Clerk
from app.configs.settings import settings
logger = get_logger(__name__)

class UserService:
    def __init__(self, crud: Optional[UserCRUD] = None):
        self.crud = crud or UserCRUD()

    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[UserResponse]:
        user = await self.crud.get_by_clerk_id(clerk_id)
        if not user:
            return None
        return UserResponse(
            clerk_id=user.clerk_id,
            emails=user.emails,
            primary_email=user.primary_email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            has_image=user.has_image,
            profile_image=user.profile_image,
            banned=user.banned,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_oauth=user.is_oauth,
            oauth_providers=user.oauth_providers,
        )

    async def create_user(self, payload: UserCreate) -> UserResponse | None:
        exists = await self.crud.get_by_email(payload.emails)
        if exists:
            raise ValueError("Email already registered")

        user = None
        try:
            user = await self.crud.create(payload)
            secret_key = generate_secret_key()
            minio_service = MinIOService()
            minio_service.create_user(str(user.id), secret_key)
            user.minio_secret_key = secret_key
            await user.save()
            return UserResponse(
                clerk_id=user.clerk_id,
                emails=user.emails,
                primary_email=user.primary_email,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                has_image=user.has_image,
                profile_image=user.profile_image,
                banned=user.banned,
                created_at=user.created_at,
                updated_at=user.updated_at,
                is_oauth=user.is_oauth,
                oauth_providers=user.oauth_providers,
            )

        except Exception as e:
            if user:
                await self.crud.delete(user, False)
            with Clerk(
                bearer_auth=settings.CLERK_SECRET_KEY,
            ) as clerk:

                res = clerk.users.delete(user_id=payload.clerk_id)
                logger.info(f"Deleted Clerk user with id {payload.clerk_id}, response: {res}")
                assert res is not None

            logger.error(f"Error creating user: {e}")
            return None

    async def update_user(self, clerk_id: str, payload: UserUpdate) -> UserResponse:
        user = await self.crud.get_by_clerk_id(clerk_id)
        if not user:
            raise ValueError("User not found")

        user = await self.crud.update(user, payload)
        return UserResponse(
            clerk_id=user.clerk_id,
            emails=user.emails,
            primary_email=user.primary_email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            has_image=user.has_image,
            profile_image=user.profile_image,
            banned=user.banned,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_oauth=user.is_oauth,
            oauth_providers=user.oauth_providers,
        )

    async def delete_user(self, clerk_id: str) -> None:
        user = await self.crud.get_by_clerk_id(clerk_id)
        if not user:
            return
        await self.crud.delete(user, False)


user_service = UserService()
