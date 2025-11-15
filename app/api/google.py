from fastapi import APIRouter, Depends, Query
from clerk_backend_api import Clerk
from starlette.status import HTTP_400_BAD_REQUEST
from typing import Optional
from app.configs.settings import settings
from app.core.exceptions import AppError
from app.utils.api_response import ok
from app.utils.verify_token import verify_token
from app.services.google_services import GoogleServices
from app.schemas.response import ApiError
from app.utils import get_logger
logger = get_logger(__name__)


router = APIRouter(
    tags=["Google Drive"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)

@router.get("/list-sheets")
async def list_sheets(
    page_token: Optional[str] = Query(None, description="Page token for pagination (from previous response)"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of files to return per page (max: 1000)"),
    current_user: dict = Depends(verify_token)
):
    """
    List Google Sheets in the user's drive with pagination support

    This endpoint retrieves a paginated list of Google Sheets from the authenticated user's Google Drive.
    Use the `next_page_token` from the response to fetch the next page.

    **Query Parameters:**
    - **page_token**: Optional. Page token from previous response to get next page
    - **page_size**: Number of files per page (1-1000, default: 50)

    **Response:**
    - **files**: List of Google Sheets with id and name
    - **next_page_token**: Token to use for next page (null if no more pages)
    - **has_more**: Boolean indicating if there are more pages available
    """
    try:
        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            res = clerk.users.get_o_auth_access_token(
                user_id=current_user.get("sub"),
                provider="oauth_google"
            )
            access_token = res[0].token

        result = await GoogleServices.async_list_sheets(access_token, page_token=page_token, page_size=page_size)

        response_data = {
            "files": result["files"],
            "next_page_token": result["next_page_token"],
            "has_more": result["next_page_token"] is not None
        }

        return ok(data=response_data, message="List google sheets successfully")

    except Exception as e:
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.get("/search-sheets")
async def search_sheets(keyword: str, current_user: dict = Depends(verify_token)):
    try:
        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            res = clerk.users.get_o_auth_access_token(
                user_id=current_user.get("sub"),
                provider="oauth_google"
            )
            access_token = res[0].token

        files = await GoogleServices.async_search_spreadsheet(access_token, keyword)
        return ok(data=files, message="Search google sheets successfully")

    except Exception as e:
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.get("/list-pdfs")
async def list_pdfs(
    page_token: Optional[str] = Query(None, description="Page token for pagination (from previous response)"),
    page_size: int = Query(50, ge=1, le=1000, description="Number of files to return per page (max: 1000)"),
    current_user: dict = Depends(verify_token)
):
    """
    List PDF files in the user's drive with pagination support

    This endpoint retrieves a paginated list of PDF files from the authenticated user's Google Drive.
    Use the `next_page_token` from the response to fetch the next page.

    **Query Parameters:**
    - **page_token**: Optional. Page token from previous response to get next page
    - **page_size**: Number of files per page (1-1000, default: 50)

    **Response:**
    - **files**: List of PDF files with id and name
    - **next_page_token**: Token to use for next page (null if no more pages)
    - **has_more**: Boolean indicating if there are more pages available
    """
    try:
        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            res = clerk.users.get_o_auth_access_token(
                user_id=current_user.get("sub"),
                provider="oauth_google"
            )
            access_token = res[0].token

        result = await GoogleServices.async_list_pdfs(access_token, page_token=page_token, page_size=page_size)

        response_data = {
            "files": result["files"],
            "next_page_token": result["next_page_token"],
            "has_more": result["next_page_token"] is not None
        }

        return ok(data=response_data, message="List PDF files successfully")

    except Exception as e:
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.get("/search-pdfs")
async def search_pdfs(keyword: str, current_user: dict = Depends(verify_token)):
    """
    Search PDF files by keyword in the user's Google Drive

    **Query Parameters:**
    - **keyword**: Search keyword to filter PDF files by name

    **Response:**
    - **files**: List of PDF files matching the keyword
    """
    try:
        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            res = clerk.users.get_o_auth_access_token(
                user_id=current_user.get("sub"),
                provider="oauth_google"
            )
            access_token = res[0].token

        files = await GoogleServices.async_search_pdf(access_token, keyword)
        return ok(data=files, message="Search PDF files successfully")

    except Exception as e:
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


