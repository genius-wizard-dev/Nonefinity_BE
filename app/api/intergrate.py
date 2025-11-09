from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from starlette.status import HTTP_400_BAD_REQUEST
from pydantic import BaseModel, Field
from app.core.exceptions import AppError
from app.utils.api_response import ok
from app.services.composio_service import ComposioService
from app.services.intergrate_service import integration_service
from app.services import user_service
from app.schemas.response import ApiError
from app.utils import get_logger
from app.schemas.intergrate import AddToolsRequest, ConnectAccountRequest
from app.utils.verify_token import verify_token
import asyncio

logger = get_logger(__name__)

router = APIRouter(
    tags=["Integrations"],
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


@router.get("")
async def list_integrations(current_user: dict = Depends(verify_token)):
    """
    List all authentication configurations from Composio with login status

    This endpoint retrieves a list of all available integration auth configs
    from Composio platform. Only returns essential fields: id, name, status, toolkit, and is_login.
    The is_login field indicates whether the user has connected this integration.

    **Response:**
    - **current_page**: Current page number
    - **items**: List of authentication configurations with is_login status
    - **total_items**: Total number of items
    - **total_pages**: Total number of pages
    - **next_cursor**: Cursor for next page (if available)
    """
    try:
        user_id = await get_user_id(current_user)
        composio_service = ComposioService()
        auth_configs = composio_service.get_list_auth_configs()

        # Get user's connected auth config IDs from MongoDB
        connected_auth_config_ids = await integration_service.get_connected_auth_config_ids(user_id)
        connected_set = set(connected_auth_config_ids)

        # Filter items to only include id, name, status, toolkit, and is_login
        filtered_items = []

        for item in auth_configs.items:
            is_login = item.id in connected_set
            filtered_item = {
                "id": item.id,
                "name": item.name,
                "status": item.status,
                "toolkit": {
                    "logo": item.toolkit.logo if item.toolkit else "",
                    "slug": item.toolkit.slug if item.toolkit else ""
                },
                "auth_scheme": item.auth_scheme,
                "is_login": is_login
            }
            filtered_items.append(filtered_item)

        # Build response with filtered items
        response_data = {
            "current_page": auth_configs.current_page,
            "items": filtered_items,
            "total_items": auth_configs.total_items,
            "total_pages": auth_configs.total_pages,
            "next_cursor": auth_configs.next_cursor
        }

        return ok(data=response_data, message="List integrations successfully")

    except Exception as e:
        logger.error(f"Error listing integrations: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


async def wait_for_connection_background(
    composio_service: ComposioService,
    connection_request,
    user_id: str,
    auth_config_id: str,
    auth_config_name: str,
    toolkit_slug: Optional[str] = None,
    toolkit_logo: Optional[str] = None
):
    """
    Background task to wait for connection to be established
    This runs in the background so the API can return immediately
    Uses asyncio.to_thread to run blocking call in thread pool
    When connection is established, saves to MongoDB with id, name, and toolkit_slug
    """
    try:
        # Run blocking call in thread pool to avoid blocking event loop
        connected_account = await asyncio.to_thread(
            composio_service.wait_for_connection,
            connection_request
        )

        if connected_account:
            # Save to MongoDB when connection is established with id, name, toolkit_slug and logo
            await integration_service.create_or_update_integration(
                user_id,
                auth_config_id,
                auth_config_name,
                toolkit_slug,
                toolkit_logo
            )
            logger.info(f"Connection established and saved to MongoDB: user {user_id}, auth_config {auth_config_id} - {auth_config_name}")
        else:
            logger.warning(f"Connection established but no connected_account returned for user {user_id}, auth_config {auth_config_id}")
    except Exception as e:
        logger.error(f"Error waiting for connection: {str(e)}")


@router.post("/connect")
async def connect_account(
    request: ConnectAccountRequest,
    current_user: dict = Depends(verify_token),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Connect user account to a Composio integration

    This endpoint initiates the OAuth flow for connecting a user's account
    to a Composio integration. It returns a redirect URL that the frontend
    should redirect the user to for authorization.

    **Request Body:**
    - **auth_config_id**: The authentication configuration ID from Composio

    **Response:**
    - **redirect_url**: URL to redirect user to for OAuth authorization
    - **message**: Success message

    **Process:**
    1. Creates a connection request with Composio
    2. Returns redirect_url immediately
    3. Frontend redirects user to the URL
    4. User authorizes the app
    5. Background task waits for connection to be established
    6. Connection status can be checked via GET endpoint

    **Example Request:**
    ```json
    {
        "auth_config_id": "ac_zRBUNNNYRl23"
    }
    ```

    **Example Response:**
    ```json
    {
        "success": true,
        "message": "Connection request created successfully",
        "data": {
            "redirect_url": "https://composio.dev/oauth/authorize?..."
        }
    }
    ```
    """
    try:
        user_id = await get_user_id(current_user)
        composio_service = ComposioService()

        # Get auth config name, toolkit_slug and logo from Composio
        auth_configs = composio_service.get_list_auth_configs()
        auth_config_name = None
        toolkit_slug = None
        toolkit_logo = None
        for item in auth_configs.items:
            if item.id == request.auth_config_id:
                auth_config_name = item.name
                toolkit_slug = item.toolkit.slug if item.toolkit else None
                toolkit_logo = item.toolkit.logo if item.toolkit else ""
                break

        if not auth_config_name:
            raise AppError(f"Auth config not found: {request.auth_config_id}", status_code=HTTP_400_BAD_REQUEST)

        # Create connection request
        connection_request = composio_service.link_account(
            user_id=user_id,
            auth_config_id=request.auth_config_id
        )

        # Get redirect URL
        redirect_url = connection_request.redirect_url

        # Add background task to wait for connection
        background_tasks.add_task(
            wait_for_connection_background,
            composio_service,
            connection_request,
            user_id,
            request.auth_config_id,
            auth_config_name,
            toolkit_slug,
            toolkit_logo
        )

        response_data = {
            "redirect_url": redirect_url
        }

        return ok(data=response_data, message="Connection request created successfully. Please redirect user to the URL for authorization.")

    except Exception as e:
        logger.error(f"Error connecting account: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)



@router.get("/tools/{toolkit_slug}")
async def get_tools(toolkit_slug: str, current_user: dict = Depends(verify_token)):
    """
    Get list of tools from Composio with is_selected status from MongoDB
    """
    try:
        user_id = await get_user_id(current_user)
        composio_service = ComposioService()
        tools = composio_service.get_list_tools_by_toolkit_slug(toolkit_slug=[toolkit_slug])

        # Get selected tools from MongoDB for this user and toolkit_slug
        selected_tool_slugs = await integration_service.get_selected_tools_by_toolkit_slug(user_id, toolkit_slug)
        selected_set = set(selected_tool_slugs)

        # Add is_selected field to each tool
        tools_with_selection = []
        for tool in tools:
            tool_with_selection = {
                **tool,
                "is_selected": tool["slug"] in selected_set
            }
            tools_with_selection.append(tool_with_selection)

        return ok(data=tools_with_selection, message="List tools successfully")
    except Exception as e:
        logger.error(f"Error getting tools: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)





@router.post("/tools/{toolkit_slug}")
async def add_tools(
    toolkit_slug: str,
    request: AddToolsRequest,
    current_user: dict = Depends(verify_token)
):
    """
    Add or update tools for a Composio integration toolkit

    This endpoint upserts tools for a specific toolkit_slug. If a config with the same
    toolkit_slug exists, it updates the tools list. Otherwise, it creates a new config.

    **Request Body:**
    - **tool_slugs**: List of tool slugs to add/update

    **Response:**
    - **message**: Success message
    - **data**: Updated integration data
    """
    try:
        user_id = await get_user_id(current_user)
        composio_service = ComposioService()

        # Get auth config info from Composio for this toolkit
        auth_configs = composio_service.get_list_auth_configs()
        auth_config_id = None
        auth_config_name = None
        toolkit_logo = None

        # Find the first auth config with matching toolkit_slug
        for item in auth_configs.items:
            if item.toolkit and item.toolkit.slug == toolkit_slug:
                auth_config_id = item.id
                auth_config_name = item.name
                toolkit_logo = item.toolkit.logo if item.toolkit else ""
                break

        if not auth_config_id:
            raise AppError(f"Auth config not found for toolkit_slug: {toolkit_slug}", status_code=HTTP_400_BAD_REQUEST)

        # Upsert tools by toolkit_slug
        await integration_service.upsert_tools_by_toolkit_slug(
            user_id=user_id,
            toolkit_slug=toolkit_slug,
            tool_slugs=request.tool_slugs,
            auth_config_id=auth_config_id,
            auth_config_name=auth_config_name,
            toolkit_logo=toolkit_logo
        )

        return ok(data=None, message="Tools updated successfully")
    except Exception as e:
        logger.error(f"Error adding tools: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)




@router.get("/config")
async def get_list_config_item_by_user_id(current_user: dict = Depends(verify_token)):
    """
    Get list of integrate by user ID
    """
    try:
        user_id = await get_user_id(current_user)
        intergrate = await integration_service.get_list_config_item_by_user_id(user_id)
        return ok(data=intergrate, message="Get integrate successfully")
    except Exception as e:
        logger.error(f"Error getting integrate: {str(e)}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)
