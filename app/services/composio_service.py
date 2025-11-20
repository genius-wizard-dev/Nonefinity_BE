import asyncio
from typing import List, Optional
from app.configs.settings import settings
from app.utils import get_logger
from composio import Composio
from composio_langchain import LangchainProvider
from composio_client.types.auth_config_list_response import AuthConfigListResponse
from composio_client.types.connected_account_retrieve_response import ConnectedAccountRetrieveResponse
from composio_client.types.tool_list_response import Item
logger = get_logger(__name__)

class ComposioService:
    def __init__(self):
        self._composio = Composio(api_key=settings.COMPOSIO_API_KEY, provider=LangchainProvider())


    def get_list_auth_configs(self) -> AuthConfigListResponse:
        """Get list of auth configs (synchronous, deprecated - use async_get_list_auth_configs)"""
        return self._composio.auth_configs.list()

    async def async_get_list_auth_configs(self) -> AuthConfigListResponse:
        """Get list of auth configs (async)"""
        return await asyncio.to_thread(self._composio.auth_configs.list)

    def link_account(self, user_id: str, auth_config_id: str):
        """
        Link a user account to an auth config and return connection request
        (synchronous, deprecated - use async_link_account)
        Returns connection request object with redirect_url
        """
        connection_request = self._composio.connected_accounts.link(
            user_id=user_id,
            auth_config_id=auth_config_id,
        )
        return connection_request

    async def async_link_account(self, user_id: str, auth_config_id: str):
        """Link a user account to an auth config (async)"""
        def _link():
            return self._composio.connected_accounts.link(
                user_id=user_id,
                auth_config_id=auth_config_id,
            )
        return await asyncio.to_thread(_link)

    def wait_for_connection(self, connection_request):
        """
        Wait for the connection to be established
        This is a blocking call, should be used in background task or separate endpoint
        """
        connected_account = connection_request.wait_for_connection()
        return connected_account

    def get_connected_account(self, connected_account_id: str) -> Optional[ConnectedAccountRetrieveResponse]:
        """
        Get connected account by ID (synchronous, deprecated - use async_get_connected_account)
        """
        try:
            return self._composio.connected_accounts.get(connected_account_id)
        except Exception as e:
            logger.error(f"Error getting connected account: {str(e)}")
            return None

    async def async_get_connected_account(self, connected_account_id: str) -> Optional[ConnectedAccountRetrieveResponse]:
        """Get connected account by ID (async)"""
        def _get():
            try:
                return self._composio.connected_accounts.get(connected_account_id)
            except Exception as e:
                logger.error(f"Error getting connected account: {str(e)}")
                return None
        return await asyncio.to_thread(_get)

    def get_list_tools_by_toolkit_slug(self, toolkit_slug: list[str]) -> List[dict]:
        """
        Get list of tools from Composio (synchronous, deprecated - use async_get_list_tools_by_toolkit_slug)
        """
        items: List[Item] = self._composio.tools.get_raw_composio_tools(toolkits=toolkit_slug)
        data = []
        for item in items:
            data.append({
                "slug": item.slug,
                "name": item.name,
                "description": item.description,
            })
        return data

    async def async_get_list_tools_by_toolkit_slug(self, toolkit_slug: list[str]) -> List[dict]:
        """Get list of tools from Composio (async)"""
        def _get_tools():
            items: List[Item] = self._composio.tools.get_raw_composio_tools(toolkits=toolkit_slug)
            data = []
            for item in items:
                data.append({
                    "slug": item.slug,
                    "name": item.name,
                    "description": item.description,
                })
            return data
        return await asyncio.to_thread(_get_tools)

    def get_list_tools(self, slug: list[str], user_id: str) -> dict:
        """Get list of tools (synchronous, deprecated - use async_get_list_tools)"""
        tools = self._composio.tools.get(tools=slug, user_id=user_id)
        return tools

    async def async_get_list_tools(self, slug: list[str], user_id: str) -> dict:
        """Get list of tools (async)"""
        def _get():
            return self._composio.tools.get(tools=slug, user_id=user_id)
        return await asyncio.to_thread(_get)


composio_service = ComposioService()
