from httpx import AsyncClient
from fastapi import Request, Header
from typing import Optional

async def get(url: str, headers: dict = None, params: dict = None, bearer_token: str = None):
    headers = headers.copy() if headers else {}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    async with AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        return response.json()

async def post(url: str, headers: dict = None, body: dict = None, bearer_token: str = None):
    headers = headers.copy() if headers else {}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    async with AsyncClient() as client:
        response = await client.post(url, headers=headers, json=body)
        return response.json()


def get_timezone_from_request(request: Request) -> Optional[str]:
    """
    Extract timezone from request headers.
    Looks for 'X-Timezone' header.

    Args:
        request: FastAPI Request object

    Returns:
        Timezone string if found, None otherwise
    """
    return request.headers.get("X-Timezone") or request.headers.get("x-timezone")


def get_timezone_header(
    x_timezone: Optional[str] = Header(None, alias="X-Timezone", description="Client timezone")
) -> Optional[str]:
    """
    FastAPI dependency to extract timezone from request header.
    Can be used as a dependency in endpoint functions.

    Usage:
        @router.get("/endpoint")
        async def my_endpoint(timezone: str = Depends(get_timezone_header)):
            ...

    Args:
        x_timezone: Timezone from X-Timezone header

    Returns:
        Timezone string if found, None otherwise
    """
    return x_timezone
