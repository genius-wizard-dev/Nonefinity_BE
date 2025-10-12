from fastapi import APIRouter, Depends
from clerk_backend_api import Clerk
from starlette.status import HTTP_400_BAD_REQUEST
from app.configs.settings import settings
from app.core.exceptions import AppError
from app.utils.api_response import ok
from app.utils.verify_token import verify_token

router = APIRouter()

@router.get("/create-token")
async def create_token(clerk_id: str):
    try:
        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            session_response = await clerk.sessions.create_async(request={"user_id": clerk_id})

            if not session_response or not session_response.id:
                raise AppError("Failed to create session", status_code=HTTP_400_BAD_REQUEST)

            token_response = await clerk.sessions.create_token_async(
                session_id=session_response.id,
                expires_in_seconds=24*60*60
            )

            if not token_response or not token_response.jwt:
                raise AppError("Failed to create token", status_code=HTTP_400_BAD_REQUEST)

            return ok({
                "token": token_response.jwt,
                "session_id": session_response.id,
                "expires_in_seconds": 24*60*60
            }, f"Create token successfully for user {clerk_id}")
    except Exception as e:
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.get("/verify-token")
async def protected_route(user = Depends(verify_token)):
    return ok(data=user, message="Get current user successfully")
