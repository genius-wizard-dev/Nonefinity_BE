"""API Key Authentication Middleware"""
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.models.api_key import APIKey
from app.crud.api_key import api_key_crud
from app.services.user import user_service
from app.utils.jwt_verification import decode_token
from app.utils import get_logger

logger = get_logger(__name__)
security = HTTPBearer()


async def verify_api_key_or_token(
    authorization_credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    Verify either API key or JWT token
    Returns user dict with 'sub' (user ID) and 'auth_type' ('api_key' or 'jwt')
    """
    token = authorization_credentials.credentials

    # Check if it's an API key (starts with nf_live_)
    if token.startswith("nf_live_"):
        return await verify_api_key(token)
    
    # Otherwise, try JWT token
    return await verify_jwt_token(token)


async def verify_api_key(api_key: str) -> dict:
    """Verify API key and return user info"""
    try:
        # Hash the provided key
        key_hash = APIKey.hash_key(api_key)
        
        # Find the API key
        api_key_doc = await api_key_crud.get_by_hash(key_hash)
        
        if not api_key_doc:
            logger.warning("Invalid API key attempted")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Check if the key is valid
        if not api_key_doc.is_valid():
            reason = "expired" if api_key_doc.is_expired() else "inactive"
            logger.warning(f"API key is {reason}: {api_key_doc.key_prefix}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"API key is {reason}"
            )
        
        # Update last_used_at (don't await to avoid blocking)
        # This is a fire-and-forget operation
        import asyncio
        asyncio.create_task(api_key_doc.mark_used())
        
        # Return user info in the same format as JWT
        return {
            "sub": api_key_doc.owner_id,
            "auth_type": "api_key",
            "permissions": api_key_doc.permissions,
            "api_key_id": str(api_key_doc.id),
            "chat_config_id": api_key_doc.chat_config_id  # Include chat config ID if scoped
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API key verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )


async def verify_jwt_token(token: str) -> dict:
    """Verify JWT token (existing Clerk authentication)"""
    try:
        user_data = decode_token(token)
        return {
            **user_data,
            "auth_type": "jwt"
        }
    except Exception as e:
        logger.error(f"JWT verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# Optional: Function to check specific permissions
def require_permission(permission: str):
    """Decorator to require specific permission from API key"""
    async def permission_checker(current_user: dict = Security(verify_api_key_or_token)) -> dict:
        # JWT tokens have all permissions
        if current_user.get("auth_type") == "jwt":
            return current_user
        
        # Check API key permissions
        permissions = current_user.get("permissions", [])
        if permission not in permissions and "*" not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        
        return current_user
    
    return permission_checker


def validate_chat_config_access(current_user: dict, chat_config_id: str) -> None:
    """
    Validate that the current user/API key has access to the specified chat config
    
    Args:
        current_user: User dict from authentication
        chat_config_id: The chat config ID to validate access to
        
    Raises:
        HTTPException: If API key is scoped and doesn't match the chat_config_id
    """
    # JWT tokens have access to all their chat configs
    if current_user.get("auth_type") == "jwt":
        return
    
    # Check if API key is scoped to a specific chat config
    api_key_chat_config = current_user.get("chat_config_id")
    
    # If API key is scoped, verify it matches the requested chat config
    if api_key_chat_config and api_key_chat_config != chat_config_id:
        logger.warning(
            f"API key {current_user.get('api_key_id')} attempted to access "
            f"chat config {chat_config_id} but is scoped to {api_key_chat_config}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This API key is not authorized to access this chat configuration"
        )
