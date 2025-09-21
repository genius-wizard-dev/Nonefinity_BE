from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.jwt_verification import decode_token

security = HTTPBearer()

async def verify_token(authorization_credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token using Clerk's JWKS"""
    token = authorization_credentials.credentials
    return decode_token(token)