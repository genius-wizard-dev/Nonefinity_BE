import jwt
import requests
from jose import jwk
from typing import Dict, Any
from app.configs.settings import settings
from app.core.exceptions import AppError
from starlette.status import HTTP_401_UNAUTHORIZED


def get_jwks() -> Dict[str, Any]:
    """Fetch JWKS from Clerk's well-known endpoint"""
    try:
        response = requests.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise AppError(f"Failed to fetch JWKS: {str(e)}", status_code=HTTP_401_UNAUTHORIZED)


def get_public_key(kid: str):
    """Get the public key for the given key ID"""
    jwks = get_jwks()
    for key in jwks['keys']:
        if key['kid'] == kid:
            return jwk.construct(key)
    raise AppError("Invalid token: Key ID not found", status_code=HTTP_401_UNAUTHORIZED)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify JWT token using Clerk's JWKS"""
    try:
        headers = jwt.get_unverified_header(token)
        kid = headers.get('kid')
        
        if not kid:
            raise AppError("Invalid token: No key ID found", status_code=HTTP_401_UNAUTHORIZED)
        
        public_key = get_public_key(kid)
        
        payload = jwt.decode(
            token, 
            public_key.to_pem().decode('utf-8'), 
            algorithms=['RS256'], 
            issuer=settings.CLERK_ISSUER,
            options={"verify_aud": False}
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AppError("Token has expired", status_code=HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError as e:
        raise AppError(f"Invalid token: {str(e)}", status_code=HTTP_401_UNAUTHORIZED)
    except Exception as e:
        raise AppError(f"Token verification failed: {str(e)}", status_code=HTTP_401_UNAUTHORIZED)
