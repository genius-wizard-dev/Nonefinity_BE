from fastapi import APIRouter, Depends
from clerk_backend_api import Clerk
from starlette.status import HTTP_400_BAD_REQUEST
from app.configs.settings import settings
from app.core.exceptions import AppError
from app.utils.api_response import ok
from app.utils.verify_token import verify_token
from app.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()




@router.get("/verify-token")
async def protected_route(user = Depends(verify_token)):
    return ok(data=user, message="Get current user successfully")


@router.get("/google-token")
async def google_token(current_user: dict = Depends(verify_token)):
    try:
        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            res = clerk.users.get_o_auth_access_token(
                user_id=current_user.get('sub'),
                provider="oauth_google"
            )
            assert res is not None

            # Extract token from response (res is a list of OAuthAccessToken objects)
            token = res[0].token if isinstance(res, list) and len(res) > 0 else res.token

            return ok({"token": token}, "Get google token successfully")
    except Exception as e:
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)



