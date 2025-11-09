from typing import List, Optional
from app.crud.intergrate import integration_crud
from app.schemas.intergrate import IntegrationResponse, IntegrationCreate, IntegrationUpdate, ConfigItemSchema
from app.utils import get_logger

logger = get_logger(__name__)


class IntegrationService:
    """Service for integration operations"""
    def __init__(self):
        self.crud = integration_crud

    async def create_or_update_integration(
        self,
        user_id: str,
        auth_config_id: str,
        auth_config_name: str,
        toolkit_slug: Optional[str] = None,
        toolkit_logo: Optional[str] = None
    ) -> IntegrationResponse:
        """Create or update integration for user (connect only, tools remain unchanged)"""
        integration = await self.crud.create_or_update(
            user_id, auth_config_id, auth_config_name, toolkit_slug, toolkit_logo
        )
        return IntegrationResponse(
            id=str(integration.id),
            user_id=integration.user_id,
            auth_config_id=integration.auth_config_id,
            auth_config_name=integration.auth_config_name,
            logo=integration.logo,
            toolkit_slug=integration.toolkit_slug,
            list_tools_slug=integration.list_tools_slug,
            created_at=integration.created_at,
            updated_at=integration.updated_at
        )

    async def upsert_tools_by_toolkit_slug(
        self,
        user_id: str,
        toolkit_slug: str,
        tool_slugs: List[str],
        auth_config_id: str,
        auth_config_name: str,
        toolkit_logo: Optional[str] = None
    ) -> IntegrationResponse:
        """Upsert tools for a toolkit_slug"""
        integration = await self.crud.upsert_tools_by_toolkit_slug(
            user_id, toolkit_slug, tool_slugs, auth_config_id, auth_config_name, toolkit_logo
        )
        return IntegrationResponse(
            id=str(integration.id),
            user_id=integration.user_id,
            auth_config_id=integration.auth_config_id,
            auth_config_name=integration.auth_config_name,
            logo=integration.logo,
            toolkit_slug=integration.toolkit_slug,
            list_tools_slug=integration.list_tools_slug,
            created_at=integration.created_at,
            updated_at=integration.updated_at
        )

    async def get_connected_auth_config_ids(self, user_id: str) -> List[str]:
        """Get list of connected auth config IDs for user"""
        return await self.crud.get_connected_auth_config_ids(user_id)

    async def get_connected_auth_configs(self, user_id: str) -> List[ConfigItemSchema]:
        """Get list of connected configs (with id, name, logo and tools) for user"""
        integrations = await self.crud.get_by_user_id(user_id)
        return [
            ConfigItemSchema(
                id=integration.auth_config_id,
                name=integration.auth_config_name,
                logo=integration.logo,
                toolkit_slug=integration.toolkit_slug,
                list_tools_slug=integration.list_tools_slug
            )
            for integration in integrations
        ]

    async def get_selected_tools_by_toolkit_slug(self, user_id: str, toolkit_slug: str) -> List[str]:
        """Get list of selected tool slugs for a specific toolkit_slug"""
        return await self.crud.get_selected_tools_by_toolkit_slug(user_id, toolkit_slug)

    async def get_tools_slug_by_user_id(self, user_id: str) -> List[str]:
        """Get list of tools slugs for a user from all integrations"""
        return await self.crud.get_tools_slug_by_user_id(user_id)

    async def get_tools_by_integration_ids(self, user_id: str, integration_ids: List[str]) -> List[str]:
        """Get list of tools by integration MongoDB IDs"""
        return await self.crud.get_tools_by_integration_ids(user_id, integration_ids)

    async def get_list_config_item_by_user_id(self, user_id: str) -> List[ConfigItemSchema]:
        """Get list of integrations by user ID, only return integrations that have tools"""
        integrations = await self.crud.get_list_config_item_by_user_id(user_id)
        return [
            ConfigItemSchema(
                id=str(integration.id),  # MongoDB ID
                name=integration.auth_config_name,
                logo=integration.logo,
                toolkit_slug=integration.toolkit_slug,
                list_tools_slug=integration.list_tools_slug
            )
            for integration in integrations
        ]

    async def remove_auth_config(self, user_id: str, auth_config_id: str) -> bool:
        """Remove integration from user"""
        return await self.crud.remove_auth_config(user_id, auth_config_id)


# Create instance
integration_service = IntegrationService()
