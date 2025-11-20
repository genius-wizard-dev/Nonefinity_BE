from typing import List
from fastapi import APIRouter, Depends, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from app.core.exceptions import AppError
from app.utils.api_response import ok
from app.services.mcp_service import mcp_service
from app.services import user_service
from app.schemas.response import ApiError
from app.schemas.mcp import MCPCreateRequest, MCPResponse, MCPListItemResponse
from app.utils.verify_token import verify_token
from app.utils import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["MCP"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)


async def get_user_id(current_user: dict) -> str:
    """Helper function to get user ID from current user"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")
    return str(user.id)


@router.post("", response_model=MCPResponse)
async def upsert_mcp_config(
    request: MCPCreateRequest,
    current_user: dict = Depends(verify_token)
):
    """
    Create or update an MCP (Model Context Protocol) configuration

    This endpoint creates a new MCP server configuration or updates an existing one
    if a configuration with the same server name already exists for the user.
    It validates the configuration by creating a MultiServerMCPClient and fetching tools.
    If validation fails, the config is not saved to MongoDB.

    **Request Body:**
    - **config**: MCP server configuration as JSON object (required)
      - The config must contain exactly one server configuration
      - The server name (key) must contain only lowercase letters, numbers, and hyphens
      - For stdio transport: command and args are required
      - For streamable_http transport: url is required
      - Example:
        {
          "server-name": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "server-name"],
            "env": {"API_KEY": "your-api-key"}
          }
        }

    **Response:**
    - **id**: MCP configuration ID
    - **owner_id**: Owner ID (user ID)
    - **name**: MCP server name (extracted from config)
    - **transport**: Transport type (extracted from config)
    - **config**: Configuration as JSON
    - **tools**: List of available tools
    """
    try:
        user_id = await get_user_id(current_user)
        # Extract server name to check if it exists before upsert
        server_name = list(request.config.keys())[0] if request.config else ""
        existing = await mcp_service.crud.get_by_user_and_server_name(user_id, server_name)
        is_new = existing is None

        mcp = await mcp_service.upsert_mcp_config(user_id, request)
        message = f"MCP config {'created' if is_new else 'updated'} successfully"
        return ok(data=mcp, message=message)
    except ValueError as e:
        logger.error(f"Validation error upserting MCP config: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error upserting MCP config: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.get("", response_model=List[MCPListItemResponse])
async def list_mcp_configs(
    current_user: dict = Depends(verify_token)
):
    """
    List all MCP configurations for the current user

    **Response:**
    - List of MCP configurations with id, name, transport, tools_count, and timestamps
    """
    try:
        user_id = await get_user_id(current_user)
        mcps = await mcp_service.get_mcp_configs(user_id)
        return ok(data=mcps, message="List MCP configs successfully")
    except Exception as e:
        logger.error(f"Error listing MCP configs: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.get("/{mcp_id}", response_model=MCPResponse)
async def get_mcp_config(
    mcp_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Get a specific MCP configuration by ID

    **Response:**
    - MCP configuration with full details including config and tools
    """
    try:
        user_id = await get_user_id(current_user)
        mcp = await mcp_service.get_mcp_config(mcp_id, user_id)
        if not mcp:
            raise AppError("MCP config not found", status_code=HTTP_400_BAD_REQUEST)
        return ok(data=mcp, message="Get MCP config successfully")
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Error getting MCP config: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.get("/{mcp_id}/tools")
async def get_mcp_tools(
    mcp_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Get tools from an MCP configuration

    This endpoint retrieves the list of tools available from the MCP server.
    If tools are not cached, it will fetch them from the MCP client.

    **Response:**
    - List of tools with name, description, and args_schema
    """
    try:
        user_id = await get_user_id(current_user)
        tools = await mcp_service.get_mcp_tools(mcp_id, user_id)
        if tools is None:
            raise AppError("MCP tools not found", status_code=HTTP_400_BAD_REQUEST)
        return ok(data=tools, message="Get MCP tools successfully")
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Error getting MCP tools: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.post("/{mcp_id}/sync", response_model=MCPResponse)
async def sync_mcp_tools(
    mcp_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Sync tools from MCP server

    This endpoint fetches the latest tools from the MCP server and updates
    them in the database. Use this when the MCP server has been updated
    and you want to refresh the tools list.

    **Response:**
    - Updated MCP configuration with synced tools
    """
    try:
        user_id = await get_user_id(current_user)
        mcp = await mcp_service.sync_mcp_tools(mcp_id, user_id)
        if not mcp:
            raise AppError("MCP config not found", status_code=HTTP_400_BAD_REQUEST)
        return ok(data=mcp, message="MCP tools synced successfully")
    except ValueError as e:
        logger.error(f"Validation error syncing MCP tools: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Error syncing MCP tools: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.delete("/{mcp_id}")
async def delete_mcp_config(
    mcp_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Delete an MCP configuration

    **Response:**
    - Success message
    """
    try:
        user_id = await get_user_id(current_user)
        deleted = await mcp_service.delete_mcp_config(mcp_id, user_id)
        if not deleted:
            raise AppError("MCP config not found", status_code=HTTP_400_BAD_REQUEST)
        return ok(data=None, message="MCP config deleted successfully")
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Error deleting MCP config: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)

