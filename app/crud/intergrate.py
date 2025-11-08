from typing import Optional, List
from app.crud.base import BaseCRUD
from app.models.intergrate import Integration, ConfigItem
from app.schemas.intergrate import IntegrationCreate, IntegrationUpdate
from app.utils import get_logger

logger = get_logger(__name__)


class IntegrationCRUD(BaseCRUD[Integration, IntegrationCreate, IntegrationUpdate]):
    def __init__(self):
        super().__init__(Integration)

    async def get_by_user_id(self, user_id: str) -> Optional[Integration]:
        """Get integration by user ID"""
        return await self.get_one(
            filter_={"user_id": user_id},
            include_deleted=False
        )

    async def create_or_update(self, user_id: str, auth_config_id: str, auth_config_name: str, toolkit_slug: Optional[str] = None, toolkit_logo: Optional[str] = None) -> Integration:
        """Create or update integration for user"""
        integration = await self.get_by_user_id(user_id)
        logo = toolkit_logo or ""

        if integration:
            # Update existing integration - add config if not exists
            existing_ids = [item.id for item in integration.configs]
            if auth_config_id not in existing_ids:
                integration.configs.append(
                    ConfigItem(id=auth_config_id, name=auth_config_name, logo=logo, toolkit_slug=toolkit_slug, list_tools_slug=[])
                )
                await integration.save()
                logger.info(f"Updated integration for user {user_id}, added config: {auth_config_id} - {auth_config_name}")
        else:
            # Create new integration
            integration = Integration(
                user_id=user_id,
                configs=[ConfigItem(id=auth_config_id, name=auth_config_name, logo=logo, toolkit_slug=toolkit_slug, list_tools_slug=[])]
            )
            await integration.insert()
            logger.info(f"Created integration for user {user_id}, config: {auth_config_id} - {auth_config_name}")

        return integration

    async def upsert_tools_by_toolkit_slug(self, user_id: str, toolkit_slug: str, tool_slugs: List[str], auth_config_id: str, auth_config_name: str, toolkit_logo: Optional[str] = None) -> Integration:
        """Upsert tools for a toolkit_slug - update existing or create new config item"""
        integration = await self.get_by_user_id(user_id)
        logo = toolkit_logo or ""

        if integration:
            # Find existing config with same toolkit_slug
            config_index = None
            for i, config in enumerate(integration.configs):
                if config.toolkit_slug == toolkit_slug:
                    config_index = i
                    break

            if config_index is not None:
                # Update existing config with new tools
                integration.configs[config_index].list_tools_slug = tool_slugs
                integration.configs[config_index].id = auth_config_id
                integration.configs[config_index].name = auth_config_name
                integration.configs[config_index].logo = logo
                await integration.save()
                logger.info(f"Updated tools for user {user_id}, toolkit_slug: {toolkit_slug}, tools: {tool_slugs}")
            else:
                # Add new config item
                integration.configs.append(
                    ConfigItem(id=auth_config_id, name=auth_config_name, logo=logo, toolkit_slug=toolkit_slug, list_tools_slug=tool_slugs)
                )
                await integration.save()
                logger.info(f"Added new config for user {user_id}, toolkit_slug: {toolkit_slug}, tools: {tool_slugs}")
        else:
            # Create new integration
            integration = Integration(
                user_id=user_id,
                configs=[ConfigItem(id=auth_config_id, name=auth_config_name, logo=logo, toolkit_slug=toolkit_slug, list_tools_slug=tool_slugs)]
            )
            await integration.insert()
            logger.info(f"Created integration for user {user_id}, toolkit_slug: {toolkit_slug}, tools: {tool_slugs}")

        return integration

    async def get_connected_auth_config_ids(self, user_id: str) -> List[str]:
        """Get list of connected auth config IDs for user"""
        integration = await self.get_by_user_id(user_id)
        if integration:
            return [item.id for item in integration.configs]
        return []

    async def get_connected_auth_configs(self, user_id: str) -> List[ConfigItem]:
        """Get list of connected configs (with id and name) for user"""
        integration = await self.get_by_user_id(user_id)
        if integration:
            return integration.configs
        return []

    async def get_selected_tools_by_toolkit_slug(self, user_id: str, toolkit_slug: str) -> List[str]:
        """Get list of selected tool slugs for a specific toolkit_slug"""
        integration = await self.get_by_user_id(user_id)
        if integration:
            for config in integration.configs:
                if config.toolkit_slug == toolkit_slug:
                    return config.list_tools_slug
        return []

    async def remove_auth_config(self, user_id: str, auth_config_id: str) -> bool:
        """Remove config from user's integration"""
        integration = await self.get_by_user_id(user_id)
        if integration:
            # Find and remove the config
            original_count = len(integration.configs)
            integration.configs = [
                item for item in integration.configs if item.id != auth_config_id
            ]
            if len(integration.configs) < original_count:
                await integration.save()
                logger.info(f"Removed config_id {auth_config_id} from user {user_id}")
                return True
        return False


# Create instance
integration_crud = IntegrationCRUD()

