import jwt
from jwt import PyJWKClient
from typing import Dict, Any
from app.configs.settings import settings
from app.core.exceptions import AppError
from starlette.status import HTTP_401_UNAUTHORIZED


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT token using Clerk's JWKS via PyJWKClient"""
    try:
        jwk_client = PyJWKClient(settings.CLERK_JWKS_URL)
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256'],
            issuer=settings.CLERK_ISSUER,
            options={"verify_aud": False}
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise AppError("Token has expired", status_code=HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError as e:
        raise AppError(f"Invalid token: {str(e)}",
                       status_code=HTTP_401_UNAUTHORIZED)
    except Exception as e:
        raise AppError(
            f"Token verification failed: {str(e)}", status_code=HTTP_401_UNAUTHORIZED)
