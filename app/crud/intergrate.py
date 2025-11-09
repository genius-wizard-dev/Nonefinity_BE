from typing import Optional, List
from app.crud.base import BaseCRUD
from app.models.intergrate import Integration
from app.schemas.intergrate import IntegrationCreate, IntegrationUpdate
from app.utils import get_logger

logger = get_logger(__name__)


class IntegrationCRUD(BaseCRUD[Integration, IntegrationCreate, IntegrationUpdate]):
    """CRUD operations for Integration"""
    def __init__(self):
        super().__init__(Integration)

    async def get_by_user_id(self, user_id: str) -> List[Integration]:
        """Get all integrations by user ID"""
        return await self.list(
            filter_={"user_id": user_id},
            include_deleted=False
        )

    async def get_by_user_and_auth_config(self, user_id: str, auth_config_id: str) -> Optional[Integration]:
        """Get integration by user ID and auth config ID"""
        return await self.get_one(
            filter_={"user_id": user_id, "auth_config_id": auth_config_id},
            include_deleted=False
        )

    async def get_by_user_and_toolkit_slug(self, user_id: str, toolkit_slug: str) -> Optional[Integration]:
        """Get integration by user ID and toolkit slug"""
        return await self.get_one(
            filter_={"user_id": user_id, "toolkit_slug": toolkit_slug},
            include_deleted=False
        )

    async def create_or_update(
        self,
        user_id: str,
        auth_config_id: str,
        auth_config_name: str,
        toolkit_slug: Optional[str] = None,
        toolkit_logo: Optional[str] = None
    ) -> Integration:
        """Create or update integration for user (connect only, tools remain unchanged)"""
        existing = await self.get_by_user_and_auth_config(user_id, auth_config_id)
        logo = toolkit_logo or ""

        if existing:
            # Update existing integration (only connection info, keep tools)
            existing.auth_config_name = auth_config_name
            existing.logo = logo
            if toolkit_slug:
                existing.toolkit_slug = toolkit_slug
            await existing.save()
            logger.info(f"Updated integration for user {user_id}, config: {auth_config_id} - {auth_config_name}")
            return existing
        else:
            # Create new integration with empty tools list
            integration = Integration(
                user_id=user_id,
                auth_config_id=auth_config_id,
                auth_config_name=auth_config_name,
                logo=logo,
                toolkit_slug=toolkit_slug,
                list_tools_slug=[]
            )
            await integration.insert()
            logger.info(f"Created integration for user {user_id}, config: {auth_config_id} - {auth_config_name}")
            return integration

    async def upsert_tools_by_toolkit_slug(
        self,
        user_id: str,
        toolkit_slug: str,
        tool_slugs: List[str],
        auth_config_id: str,
        auth_config_name: str,
        toolkit_logo: Optional[str] = None
    ) -> Integration:
        """Upsert tools for a toolkit_slug - update existing or create new integration"""
        existing = await self.get_by_user_and_toolkit_slug(user_id, toolkit_slug)
        logo = toolkit_logo or ""

        if existing:
            # Update existing integration with new tools
            existing.list_tools_slug = tool_slugs
            existing.auth_config_id = auth_config_id
            existing.auth_config_name = auth_config_name
            existing.logo = logo
            await existing.save()
            logger.info(f"Updated tools for user {user_id}, toolkit_slug: {toolkit_slug}, tools: {tool_slugs}")
            return existing
        else:
            # Create new integration with tools
            integration = Integration(
                user_id=user_id,
                auth_config_id=auth_config_id,
                auth_config_name=auth_config_name,
                logo=logo,
                toolkit_slug=toolkit_slug,
                list_tools_slug=tool_slugs
            )
            await integration.insert()
            logger.info(f"Created integration for user {user_id}, toolkit_slug: {toolkit_slug}, tools: {tool_slugs}")
            return integration

    async def get_connected_auth_config_ids(self, user_id: str) -> List[str]:
        """Get list of connected auth config IDs for user"""
        integrations = await self.get_by_user_id(user_id)
        return [integration.auth_config_id for integration in integrations]

    async def get_selected_tools_by_toolkit_slug(self, user_id: str, toolkit_slug: str) -> List[str]:
        """Get list of selected tool slugs for a specific toolkit_slug"""
        integration = await self.get_by_user_and_toolkit_slug(user_id, toolkit_slug)
        if integration:
            return integration.list_tools_slug
        return []

    async def get_tools_slug_by_user_id(self, user_id: str) -> List[str]:
        """Get list of tools slugs for a user from all integrations"""
        integrations = await self.get_by_user_id(user_id)
        # Flatten list of tools from all integrations
        return [tool_slug for integration in integrations for tool_slug in integration.list_tools_slug]

    async def get_tools_by_integration_ids(self, user_id: str, integration_ids: List[str]) -> List[str]:
        """Get list of tools by integration MongoDB IDs"""
        integrations = await self.get_by_user_id(user_id)
        return [
            tool_slug
            for integration in integrations
            for tool_slug in integration.list_tools_slug
            if str(integration.id) in integration_ids
        ]

    async def get_list_config_item_by_user_id(self, user_id: str) -> List[Integration]:
        """Get list of integrations by user ID, only return integrations that have tools"""
        integrations = await self.get_by_user_id(user_id)
        # Filter integrations that have at least one tool
        return [integration for integration in integrations if integration.list_tools_slug]

    async def remove_auth_config(self, user_id: str, auth_config_id: str) -> bool:
        """Remove integration from user"""
        integration = await self.get_by_user_and_auth_config(user_id, auth_config_id)
        if integration:
            await self.delete(integration)
            logger.info(f"Removed integration {auth_config_id} from user {user_id}")
            return True
        return False


# Create instance
integration_crud = IntegrationCRUD()
