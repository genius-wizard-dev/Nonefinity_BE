from httpx import AsyncClient

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
