from typing import Optional, List
from app.crud.base import BaseCRUD
from app.models.mcp import MCP
from app.schemas.mcp import MCPCreateRequest, MCPUpdateRequest
from app.utils import get_logger
from bson import ObjectId
logger = get_logger(__name__)


class MCPCRUD(BaseCRUD[MCP, MCPCreateRequest, MCPUpdateRequest]):
    """CRUD operations for MCP"""
    def __init__(self):
        super().__init__(MCP)

    async def get_by_user_id(self, user_id: str) -> List[MCP]:
        """Get all MCP configs by user ID"""
        return await self.list(
            filter_={"owner_id": user_id},
            include_deleted=False
        )

    async def get_by_user_and_server_name(self, user_id: str, server_name: str) -> Optional[MCP]:
        """Get MCP config by user ID and server name (from config key)"""
        mcps = await self.get_by_user_id(user_id)
        for mcp in mcps:
            if mcp.server_name == server_name:
                return mcp
        return None

    async def get_by_id_and_user(self, mcp_id: str, user_id: str) -> Optional[MCP]:
        """Get MCP config by ID and user ID"""
        return await self.get_one(
            filter_={"_id": ObjectId(mcp_id), "owner_id": user_id},
            include_deleted=False
        )

    async def create_or_update(
        self,
        user_id: str,
        name: str,
        description: Optional[str],
        config: dict,
        tools: Optional[List[dict]] = None
    ) -> MCP:
        """Create or update MCP config"""
        # Extract server name from config
        server_name = list(config.keys())[0] if config else ""

        existing = await self.get_by_user_and_server_name(user_id, server_name)

        if existing:
            # Update existing MCP config
            existing.name = name
            existing.description = description
            existing.config = config
            if tools is not None:
                existing.tools = tools
            await existing.save()
            logger.info(f"Updated MCP config for user {user_id}, server: {server_name}")
            return existing
        else:
            # Create new MCP config
            mcp = MCP(
                owner_id=user_id,
                name=name,
                description=description,
                config=config,
                tools=tools
            )
            await mcp.insert()
            logger.info(f"Created MCP config for user {user_id}, server: {server_name}")
            return mcp

    async def update_tools(self, mcp_id: str, user_id: str, tools: List[dict]) -> Optional[MCP]:
        """Update tools for an MCP config"""
        mcp = await self.get_by_id_and_user(mcp_id, user_id)
        if mcp:
            mcp.tools = tools
            await mcp.save()
            logger.info(f"Updated tools for MCP {mcp_id}")
            return mcp
        return None

    async def delete_by_id_and_user(self, mcp_id: str, user_id: str) -> bool:
        """Delete MCP config by ID and user ID"""
        mcp = await self.get_by_id_and_user(mcp_id, user_id)
        if mcp:
            await self.delete(mcp)
            logger.info(f"Deleted MCP {mcp_id} for user {user_id}")
            return True
        return False


# Create instance
mcp_crud = MCPCRUD()

