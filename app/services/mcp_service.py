from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools.base import BaseTool
from typing import List, Optional, Dict, Any
from app.crud.mcp import mcp_crud
from app.schemas.mcp import MCPResponse, MCPListItemResponse, MCPCreateRequest
from app.utils import get_logger

logger = get_logger(__name__)


class MCPService:
    """Service for MCP operations"""
    def __init__(self):
        self.crud = mcp_crud

    async def upsert_mcp_config(
        self,
        user_id: str,
        request: MCPCreateRequest
    ) -> MCPResponse:
        """Create or update MCP config with validation using MultiServerMCPClient"""
        try:
            # Config is already in the correct format: {server_name: {config}}
            client_config = request.config

            # Validate by creating client and getting tools
            client = MultiServerMCPClient(client_config)
            tools = await client.get_tools()

            # Convert tools to list of dicts for storage
            tools_list = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name if hasattr(tool, "name") else str(tool),
                    "description": tool.description if hasattr(tool, "description") else "",
                }
                # Add more fields if available
                if hasattr(tool, "args_schema"):
                    tool_dict["args_schema"] = str(tool.args_schema)
                tools_list.append(tool_dict)

            # Upsert to MongoDB (create or update)
            mcp = await self.crud.create_or_update(
                user_id=user_id,
                name=request.name,
                description=request.description,
                config=request.config,
                tools=tools_list
            )

            return MCPResponse(
                id=str(mcp.id),
                owner_id=mcp.owner_id,
                name=mcp.name,
                description=mcp.description,
                server_name=mcp.server_name,
                transport=mcp.transport,
                config=mcp.config,
                tools=mcp.tools,
                created_at=mcp.created_at,
                updated_at=mcp.updated_at
            )
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error upserting MCP config: {str(e)}")
            raise ValueError(f"Failed to validate MCP config: {str(e)}")

    async def get_mcp_configs(self, user_id: str) -> List[MCPListItemResponse]:
        """Get list of MCP configs for user"""
        mcps = await self.crud.get_by_user_id(user_id)
        return [
            MCPListItemResponse(
                id=str(mcp.id),
                name=mcp.name,
                description=mcp.description,
                server_name=mcp.server_name,
                transport=mcp.transport,
                tools_count=len(mcp.tools) if mcp.tools else 0,
                created_at=mcp.created_at,
                updated_at=mcp.updated_at
            )
            for mcp in mcps
        ]

    async def get_mcp_config(self, mcp_id: str, user_id: str) -> Optional[MCPResponse]:
        """Get MCP config by ID"""
        mcp = await self.crud.get_by_id_and_user(mcp_id, user_id)
        if not mcp:
            return None

        return MCPResponse(
            id=str(mcp.id),
            owner_id=mcp.owner_id,
            name=mcp.name,
            description=mcp.description,
            server_name=mcp.server_name,
            transport=mcp.transport,
            config=mcp.config,
            tools=mcp.tools,
            created_at=mcp.created_at,
            updated_at=mcp.updated_at
        )

    async def get_mcp_tools(self, mcp_id: str, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get tools from MCP config"""
        mcp = await self.crud.get_by_id_and_user(mcp_id, user_id)
        if not mcp:
            return None

        # If tools are already stored, return them
        if mcp.tools:
            return mcp.tools

        try:
            client_config = mcp.config
            client = MultiServerMCPClient(client_config)
            tools = await client.get_tools()

            # Convert tools to list of dicts
            tools_list = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name if hasattr(tool, "name") else str(tool),
                    "description": tool.description if hasattr(tool, "description") else "",
                }
                if hasattr(tool, "args_schema"):
                    tool_dict["args_schema"] = str(tool.args_schema)
                tools_list.append(tool_dict)

            # Update tools in database
            await self.crud.update_tools(mcp_id, user_id, tools_list)

            return tools_list
        except Exception as e:
            logger.error(f"Error fetching tools from MCP: {str(e)}")
            return []

    async def sync_mcp_tools(self, mcp_id: str, user_id: str) -> Optional[MCPResponse]:
        """Sync tools from MCP server and update in database"""
        mcp = await self.crud.get_by_id_and_user(mcp_id, user_id)
        if not mcp:
            return None

        try:
            # Fetch tools from MCP client
            client_config = mcp.config
            client = MultiServerMCPClient(client_config)
            tools = await client.get_tools()

            # Convert tools to list of dicts
            tools_list = []
            for tool in tools:
                tool_dict = {
                    "name": tool.name if hasattr(tool, "name") else str(tool),
                    "description": tool.description if hasattr(tool, "description") else "",
                }
                if hasattr(tool, "args_schema"):
                    tool_dict["args_schema"] = str(tool.args_schema)
                tools_list.append(tool_dict)

            # Update tools in database
            await self.crud.update_tools(mcp_id, user_id, tools_list)

            # Get updated MCP config
            updated_mcp = await self.crud.get_by_id_and_user(mcp_id, user_id)
            if not updated_mcp:
                return None

            return MCPResponse(
                id=str(updated_mcp.id),
                owner_id=updated_mcp.owner_id,
                name=updated_mcp.name,
                description=updated_mcp.description,
                server_name=updated_mcp.server_name,
                transport=updated_mcp.transport,
                config=updated_mcp.config,
                tools=updated_mcp.tools,
                created_at=updated_mcp.created_at,
                updated_at=updated_mcp.updated_at
            )
        except Exception as e:
            logger.error(f"Error syncing tools from MCP: {str(e)}")
            raise ValueError(f"Failed to sync tools from MCP: {str(e)}")

    async def delete_mcp_config(self, mcp_id: str, user_id: str) -> bool:
        """Delete MCP config"""
        return await self.crud.delete_by_id_and_user(mcp_id, user_id)

    async def get_tools_by_mcp_ids(self, user_id: str, mcp_ids: List[str]) -> List[BaseTool]:
        """Get tools by MCP IDs - merges configs and gets tools from MCP client

        Returns BaseTool objects that can be used directly in LangChain agents.
        The configs are merged into format: {server_name: {config}}
        """
        if not mcp_ids:
            return []

        # Get all MCP configs by IDs
        mcps = []
        for mcp_id in mcp_ids:
            mcp = await self.crud.get_by_id_and_user(mcp_id, user_id)
            if mcp:
                mcps.append(mcp)

        if not mcps:
            logger.warning(f"No MCP configs found for IDs: {mcp_ids}")
            return []

        try:
            # Merge all MCP configs into one dict
            # Format: {server_name: {config}}
            # Example: {
            #   "math": {"transport": "stdio", "command": "python", "args": ["/path/to/math_server.py"]},
            #   "weather": {"transport": "streamable_http", "url": "http://localhost:8000/mcp"}
            # }
            merged_config = {}
            for mcp in mcps:
                # mcp.config is already in format {server_name: {config}}
                merged_config.update(mcp.config)

            # Create MultiServerMCPClient with merged config
            client = MultiServerMCPClient(merged_config)

            # Get tools from MCP client (returns List[BaseTool])
            tools = await client.get_tools()

            return tools

        except Exception as e:
            logger.error(f"Error fetching tools from MCP configs: {str(e)}")
            logger.exception(e)
            # Return empty list on error - tools will be unavailable but won't break the chat
            return []

    async def get_tools_by_mcp_id(self, user_id: str, mcp_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get tools by MCP ID"""
        mcp = await self.crud.get_by_id_and_user(mcp_id, user_id)
        if not mcp:
            return None
        return mcp.tools


# Create instance
mcp_service = MCPService()

