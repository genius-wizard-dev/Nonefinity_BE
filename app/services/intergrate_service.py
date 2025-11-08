from typing import List, Optional
from app.crud.intergrate import integration_crud
from app.schemas.intergrate import IntegrationResponse, IntegrationCreate, IntegrationUpdate, ConfigItemSchema
from app.utils import get_logger

logger = get_logger(__name__)


class IntegrationService:
    def __init__(self):
        self.crud = integration_crud

    async def create_or_update_integration(self, user_id: str, auth_config_id: str, auth_config_name: str, toolkit_slug: Optional[str] = None, toolkit_logo: Optional[str] = None) -> IntegrationResponse:
        """Create or update integration for user"""
        integration = await self.crud.create_or_update(user_id, auth_config_id, auth_config_name, toolkit_slug, toolkit_logo)
        return IntegrationResponse(
            id=str(integration.id),
            user_id=integration.user_id,
            configs=[
                ConfigItemSchema(id=item.id, name=item.name, logo=item.logo, toolkit_slug=item.toolkit_slug, list_tools_slug=item.list_tools_slug)
                for item in integration.configs
            ],
            created_at=integration.created_at,
            updated_at=integration.updated_at
        )

    async def upsert_tools_by_toolkit_slug(self, user_id: str, toolkit_slug: str, tool_slugs: List[str], auth_config_id: str, auth_config_name: str, toolkit_logo: Optional[str] = None) -> IntegrationResponse:
        """Upsert tools for a toolkit_slug"""
        integration = await self.crud.upsert_tools_by_toolkit_slug(user_id, toolkit_slug, tool_slugs, auth_config_id, auth_config_name, toolkit_logo)
        return IntegrationResponse(
            id=str(integration.id),
            user_id=integration.user_id,
            configs=[
                ConfigItemSchema(id=item.id, name=item.name, logo=item.logo, toolkit_slug=item.toolkit_slug, list_tools_slug=item.list_tools_slug)
                for item in integration.configs
            ],
            created_at=integration.created_at,
            updated_at=integration.updated_at
        )

    async def get_user_integration(self, user_id: str) -> Optional[IntegrationResponse]:
        """Get integration for user"""
        integration = await self.crud.get_by_user_id(user_id)
        if not integration:
            return None

        return IntegrationResponse(
            id=str(integration.id),
            user_id=integration.user_id,
            configs=[
                ConfigItemSchema(id=item.id, name=item.name, logo=item.logo, toolkit_slug=item.toolkit_slug, list_tools_slug=item.list_tools_slug)
                for item in integration.configs
            ],
            created_at=integration.created_at,
            updated_at=integration.updated_at
        )

    async def get_connected_auth_config_ids(self, user_id: str) -> List[str]:
        """Get list of connected auth config IDs for user"""
        return await self.crud.get_connected_auth_config_ids(user_id)

    async def get_connected_auth_configs(self, user_id: str) -> List[ConfigItemSchema]:
        """Get list of connected configs (with id, name and logo) for user"""
        configs = await self.crud.get_connected_auth_configs(user_id)
        return [
            ConfigItemSchema(id=item.id, name=item.name, logo=item.logo, toolkit_slug=item.toolkit_slug, list_tools_slug=item.list_tools_slug)
            for item in configs
        ]

    async def get_selected_tools_by_toolkit_slug(self, user_id: str, toolkit_slug: str) -> List[str]:
        """Get list of selected tool slugs for a specific toolkit_slug"""
        return await self.crud.get_selected_tools_by_toolkit_slug(user_id, toolkit_slug)

    async def remove_auth_config(self, user_id: str, auth_config_id: str) -> bool:
        """Remove config from user's integration"""
        return await self.crud.remove_auth_config(user_id, auth_config_id)



# Create instance
integration_service = IntegrationService()

