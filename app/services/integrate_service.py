from typing import List, Optional
from app.crud.integrate import integration_crud
from app.schemas.integrate import IntegrationResponse, ConfigItemSchema
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
        """Create or update integration for user (connect only)"""
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
            created_at=integration.created_at,
            updated_at=integration.updated_at
        )

    async def get_connected_auth_config_ids(self, user_id: str) -> List[str]:
        """Get list of connected auth config IDs for user"""
        return await self.crud.get_connected_auth_config_ids(user_id)

    async def get_connected_auth_configs(self, user_id: str) -> List[ConfigItemSchema]:
        """Get list of connected configs (with id, name, logo) for user"""
        integrations = await self.crud.get_by_user_id(user_id)
        return [
            ConfigItemSchema(
                id=str(integration.id),
                name=integration.auth_config_name,
                logo=integration.logo,
                toolkit_slug=integration.toolkit_slug
            )
            for integration in integrations
        ]

    async def get_list_config_item_by_user_id(self, user_id: str) -> List[ConfigItemSchema]:
        """Get list of all integrations by user ID"""
        integrations = await self.crud.get_all_connected_integrations(user_id)
        return [
            ConfigItemSchema(
                id=str(integration.id),  # MongoDB ID
                name=integration.auth_config_name,
                logo=integration.logo,
                toolkit_slug=integration.toolkit_slug
            )
            for integration in integrations
        ]

    async def remove_auth_config(self, user_id: str, auth_config_id: str) -> bool:
        """Remove integration from user"""
        return await self.crud.remove_auth_config(user_id, auth_config_id)

    async def get_selected_tools_by_toolkit_slug(self, user_id: str, toolkit_slug: str) -> List[str]:
        """Get list of selected tool slugs for a user and toolkit_slug"""
        return await self.crud.get_selected_tools_by_toolkit_slug(user_id, toolkit_slug)

    async def upsert_tools_by_toolkit_slug(
        self,
        user_id: str,
        toolkit_slug: str,
        tool_slugs: List[str],
        auth_config_id: str,
        auth_config_name: str,
        toolkit_logo: Optional[str] = None
    ) -> None:
        """Upsert integration with tools by toolkit_slug"""
        await self.crud.upsert_tools_by_toolkit_slug(
            user_id=user_id,
            toolkit_slug=toolkit_slug,
            tool_slugs=tool_slugs,
            auth_config_id=auth_config_id,
            auth_config_name=auth_config_name,
            toolkit_logo=toolkit_logo
        )


# Create instance
integration_service = IntegrationService()
