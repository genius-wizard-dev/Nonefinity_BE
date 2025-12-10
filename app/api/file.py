from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from app.services import FileService, user_service
from app.services.google_services import GoogleServices
from app.schemas.response import ApiResponse, ApiError
from starlette.status import HTTP_400_BAD_REQUEST
from app.core.exceptions import AppError
from app.schemas.file import (
    FileResponse, FileUpdate, BatchDeleteRequest, UploadUrlRequest,
    UploadUrlResponse, FileMetadataRequest
)
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from app.utils.cache_decorator import cache_list, invalidate_cache
from app.utils import get_logger
from app.configs.settings import settings
from clerk_backend_api import Clerk
from pydantic import BaseModel, Field, validator, model_validator
from typing import Optional, List
import re

logger = get_logger(__name__)

router = APIRouter(
    tags=["Files"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)

@router.post(
    "/upload-url",
    response_model=ApiResponse[UploadUrlResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Presigned Upload URL",
    description="Generate a presigned URL for direct file upload to MinIO storage",
    responses={
        200: {"description": "Upload URL generated successfully"},
        400: {"description": "Invalid request or user not found"},
        401: {"description": "Authentication required"}
    }
)

async def get_upload_url(
    request: UploadUrlRequest,
    current_user = Depends(verify_token)
):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    try:
        upload_data = await file_service.get_upload_url(
            user_id=user_id,
            file_name=request.file_name,
            file_type=request.file_type
        )

        return ok(data=upload_data, message="Upload URL generated successfully")
    except AppError as e:
        raise e
    except Exception:
        raise AppError("Failed to generate upload URL", status_code=HTTP_400_BAD_REQUEST)

@router.post(
    "/upload",
    response_model=ApiResponse[FileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Save File Metadata",
    description="Save file metadata after successful upload to MinIO storage",
    responses={
        201: {"description": "File metadata saved successfully"},
        400: {"description": "Invalid request or user not found"},
        401: {"description": "Authentication required"}
    }
)
@invalidate_cache("files")
async def save_file_metadata(
    request: FileMetadataRequest,
    current_user = Depends(verify_token)
):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    try:
        # Set source_file to "upload" for regular uploads
        file_created = await file_service.save_file_metadata(
            user_id=user_id,
            object_name=request.object_name,
            file_name=request.file_name,
            file_type=request.file_type,
            file_size=request.file_size,
            source_file="upload"
        )

        # Convert File model to FileResponse
        result = FileResponse(
            id=str(file_created.id),
            owner_id=file_created.owner_id,
            bucket=file_created.bucket,
            file_path=file_created.file_path,
            file_name=file_created.file_name,
            file_ext=file_created.file_ext,
            file_type=file_created.file_type,
            file_size=file_created.file_size,
            source_file=getattr(file_created, 'source_file', 'upload'),
            created_at=file_created.created_at,
            updated_at=file_created.updated_at
        )

        return created(result, message="File metadata saved successfully")
    except AppError as e:
        raise e
    except Exception:
        raise AppError("Failed to save file metadata", status_code=HTTP_400_BAD_REQUEST)

@router.delete(
    "/{file_id}",
    response_model=ApiResponse[bool],
    status_code=status.HTTP_200_OK,
    summary="Delete File",
    description="Delete a file from storage and database",
    responses={
        200: {"description": "File deleted successfully"},
        400: {"description": "File deletion failed"},
        401: {"description": "Authentication required"},
        404: {"description": "File not found"}
    }
)
@invalidate_cache("files")
async def delete_file(
    file_id: str = Path(..., description="File ID to delete"),
    current_user = Depends(verify_token)
):

    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    result = await file_service.delete_file(user_id=user_id, file_id=file_id)
    if not result:
        raise AppError("File deletion failed", status_code=HTTP_400_BAD_REQUEST)

    return ok(message="File deleted successfully")


@router.get(
    "/list",
    response_model=ApiResponse[List[FileResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Files",
    description="Get a list of all files for the current user",
    responses={
        200: {"description": "Files retrieved successfully"},
        401: {"description": "Authentication required"},
        500: {"description": "Internal server error"}
    }
)
async def list_files(current_user = Depends(verify_token)):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    files = await file_service.list_files(user_id=user_id)
    if files is None:
        raise AppError("Failed to list files", status_code=HTTP_400_BAD_REQUEST)

    # Convert File model to FileResponse
    file_responses = [
        FileResponse(
            id=str(file.id),
            owner_id=file.owner_id,
            bucket=file.bucket,
            file_path=file.file_path,
            file_name=file.file_name,
            file_ext=file.file_ext,
            file_type=file.file_type,
            file_size=file.file_size,
            source_file=getattr(file, 'source_file', 'upload'),
            created_at=file.created_at,
            updated_at=file.updated_at
        )
        for file in files
    ]

    return ok(data=file_responses, message="Files listed successfully")

@router.put("/rename/{file_id}", response_model=ApiResponse[FileResponse])
@invalidate_cache("files")
async def rename_file(file_id: str, new_name: str, current_user = Depends(verify_token)):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)
    file = await file_service.crud.get_by_id(file_id)
    if not file or file.owner_id != user_id:
        raise AppError("File not found", status_code=HTTP_400_BAD_REQUEST)


    update_data = FileUpdate(file_name=new_name)
    updated_file = await file_service.crud.update(file, obj_in=update_data)
    return ok(data=updated_file, message="File renamed successfully")

@router.get("/download/{file_id}", response_model=ApiResponse[str])
@cache_list("files", ttl=300)
async def get_download_url(file_id: str, current_user = Depends(verify_token)):
    try:
        clerk_id = current_user.get("sub")
        user = await user_service.crud.get_by_clerk_id(clerk_id)
        user_id = str(user.id)

        if not user or not user.minio_secret_key:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

        file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

        download_url = await file_service.get_download_url(user_id, file_id)
        if not download_url:
            raise AppError("File not found", status_code=HTTP_400_BAD_REQUEST)

        return ok(data=download_url, message="Download URL generated successfully")
    except HTTPException:
        raise
    except AppError as e:
        raise e
    except Exception:
        raise AppError("Failed to generate download URL", status_code=HTTP_400_BAD_REQUEST)



@router.get("/search", response_model=ApiResponse[List[FileResponse]])
@cache_list("files", ttl=300)
async def search_files(
    q: str = Query(..., description="Search term"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    current_user = Depends(verify_token)
):
    """Search files by name in raw/ folder

    Args:
        q: Search term
        file_type: Filter by file type
        limit: Number of results to return
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    if file_type:
        files = await file_service.crud.get_files_by_type(user_id, file_type, limit)
        # Filter by name if search term provided
        if q:
            files = [f for f in files if q.lower() in f.file_name.lower()]
    else:
        files = await file_service.crud.search_files_by_name(user_id, q, limit)

    # Convert File model to FileResponse
    file_responses = [
        FileResponse(
            id=str(file.id),
            owner_id=file.owner_id,
            bucket=file.bucket,
            file_path=file.file_path,
            file_name=file.file_name,
            file_ext=file.file_ext,
            file_type=file.file_type,
            file_size=file.file_size,
            source_file=getattr(file, 'source_file', 'upload'),
            created_at=file.created_at,
            updated_at=file.updated_at
        )
        for file in files
    ]

    return ok(data=file_responses, message="Search completed successfully")

@router.get("/stats", response_model=ApiResponse[dict])
async def get_file_stats(current_user = Depends(verify_token)):
    """Get file statistics for raw/ folder

    Args:
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    # Get files in raw folder only
    all_files = await file_service.crud.list({"owner_id": user_id}, include_deleted=False)
    total_files = len(all_files)
    total_size = sum(f.file_size or 0 for f in all_files)

    # Group by file type (structured vs unstructured)
    file_types = {
        "structured": 0,
        "unstructured": 0
    }

    structured_mime_types = [
        "text/csv",
        "application/csv",
        "text/x-csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        "application/json",
        "application/xml",
        "text/xml"
    ]

    for file in all_files:
        ft = file.file_type.lower() if file.file_type else ""
        if any(mime in ft for mime in structured_mime_types):
             file_types["structured"] += 1
        else:
             file_types["unstructured"] += 1

    stats = {
        "total_files": total_files,
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
        "file_types": file_types
    }

    return ok(data=stats, message="Statistics retrieved successfully")

@router.get("/types", response_model=ApiResponse[List[str]])
@cache_list("files", ttl=300)
async def get_file_types(current_user = Depends(verify_token)):
    """Get all unique file types in raw/ folder

    Args:
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    # Get distinct file types using aggregation
    pipeline = [
        {"$match": {"owner_id": user_id, "deleted_at": None}},
        {"$group": {"_id": "$file_type"}},
        {"$sort": {"_id": 1}}
    ]

    from app.models.file import File
    result = await File.get_pymongo_collection().aggregate(pipeline).to_list()
    file_types = [item["_id"] for item in result if item["_id"]]

    return ok(data=file_types, message="File types retrieved successfully")


@router.post("/batch/delete", response_model=ApiResponse[dict])
@invalidate_cache("files")
async def batch_delete_files(
    request: BatchDeleteRequest,
    current_user = Depends(verify_token)
):
    """Delete multiple files at once from raw/ folder

    Args:
        request: Batch delete request containing file IDs
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    results = await file_service.batch_delete_files(user_id, request.file_ids)

    return ok(data=results, message=f"Batch deletion completed. {len(results['successful'])} successful, {len(results['failed'])} failed")

@router.get("/allow-convert", response_model=ApiResponse[List[FileResponse]])
@cache_list("files", ttl=300)
async def get_list_allow_convert(current_user = Depends(verify_token)):
    """Get list of files that are allowed to be converted to dataset"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    files = await file_service.get_list_allow_convert(user_id)

    # Convert File model to FileResponse
    file_responses = [
        FileResponse(
            id=str(file.id),
            owner_id=file.owner_id,
            bucket=file.bucket,
            file_path=file.file_path,
            file_name=file.file_name,
            file_ext=file.file_ext,
            file_type=file.file_type,
            file_size=file.file_size,
            source_file=getattr(file, 'source_file', 'upload'),
            created_at=file.created_at,
            updated_at=file.updated_at
        )
        for file in files
    ]

    return ok(data=file_responses, message="List of files that are allowed to be converted to dataset retrieved successfully")


@router.get("/allow-extract", response_model=ApiResponse[List[FileResponse]])

async def get_list_allow_extract(current_user = Depends(verify_token)):
    """Get list of files that are allowed to be extracted"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    files = await file_service.get_list_allow_extract(user_id)

    # Convert File model to FileResponse
    file_responses = [
        FileResponse(
            id=str(file.id),
            owner_id=file.owner_id,
            bucket=file.bucket,
            file_path=file.file_path,
            file_name=file.file_name,
            file_ext=file.file_ext,
            file_type=file.file_type,
            file_size=file.file_size,
            source_file=getattr(file, 'source_file', 'upload'),
            created_at=file.created_at,
            updated_at=file.updated_at
        )
        for file in files
    ]

    return ok(data=file_responses, message="List of files that are allowed to be extracted retrieved successfully")


# Import from Google Drive schemas
class ImportFilesRequest(BaseModel):
    """Schema for importing files from Google Drive"""
    file_ids: List[str] = Field(..., min_items=1, description="List of Google Drive file IDs")
    file_types: List[str] = Field(..., min_items=1, description="List of file types (sheet/pdf)")

    @validator('file_types')
    def validate_file_types(cls, v):
        allowed_types = ['sheet', 'pdf']
        for file_type in v:
            if file_type not in allowed_types:
                raise ValueError(f"File type must be one of {allowed_types}")
        return v

    @model_validator(mode='after')
    def validate_lists_match(self):
        if len(self.file_ids) != len(self.file_types):
            raise ValueError("file_ids and file_types must have the same length")
        return self


class ImportSheetUrlRequest(BaseModel):
    """Schema for importing sheet from URL"""
    sheet_url: str = Field(..., description="Google Sheet URL")

    @validator('sheet_url')
    def validate_sheet_url(cls, v):
        if not v.strip():
            raise ValueError("Sheet URL cannot be empty")
        # Extract sheet ID from various Google Sheets URL formats
        patterns = [
            r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
            r'/([a-zA-Z0-9-_]{44})',  # Standard sheet ID length
        ]
        for pattern in patterns:
            match = re.search(pattern, v)
            if match:
                return v
        raise ValueError("Invalid Google Sheet URL format")


@router.post(
    "/import-from-drive",
    response_model=ApiResponse[List[FileResponse]],
    status_code=status.HTTP_201_CREATED,
    summary="Import Files from Google Drive",
    description="Import multiple files from Google Drive to MinIO storage. Sets source_file to 'drive'."
)
@invalidate_cache("files")
async def import_files_from_drive(
    request: ImportFilesRequest,
    current_user: dict = Depends(verify_token)
):
    """
    Import files from Google Drive to MinIO storage

    This endpoint imports multiple files from Google Drive (Sheets or PDFs) to the user's MinIO storage.
    Files are downloaded from Drive, uploaded to MinIO, and metadata is saved to the database with source_file='drive'.

    **Request Body:**
    - **file_ids**: List of Google Drive file IDs
    - **file_types**: List of file types ('sheet' or 'pdf') corresponding to each file_id

    **Response:**
    - List of imported files with metadata (source_file='drive')
    """
    try:
        # Get user and access token
        clerk_id = current_user.get("sub")
        user = await user_service.crud.get_by_clerk_id(clerk_id)
        if not user or not user.minio_secret_key:
            raise AppError("User not found", status_code=HTTP_400_BAD_REQUEST)

        user_id = str(user.id)

        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            res = clerk.users.get_o_auth_access_token(
                user_id=clerk_id,
                provider="oauth_google"
            )
            access_token = res[0].token

        # Initialize file service
        file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

        # Import files
        imported_files = []
        errors = []

        for file_id, file_type in zip(request.file_ids, request.file_types):
            try:
                logger.info(f"[API_IMPORT] Processing file - file_id: {file_id}, type: {file_type}, user_id: {user_id}")
                # Get file info to get the name
                file_info = GoogleServices.get_file_info(access_token, file_id)
                file_name = file_info.get("name", f"file_{file_id}")
                logger.info(f"[API_IMPORT] File info - name: {file_name}")

                # Import file (source_file will be set to "drive" in import_from_drive)
                imported_file = await file_service.import_from_drive(
                    user_id=user_id,
                    file_id=file_id,
                    file_name=file_name,
                    file_type=file_type,
                    access_token=access_token
                )
                logger.info(f"[API_IMPORT] Successfully imported - file_id: {imported_file.id}, name: {file_name}, source: {imported_file.source_file}")

                # Convert to FileResponse
                file_response = FileResponse(
                    id=str(imported_file.id),
                    owner_id=imported_file.owner_id,
                    bucket=imported_file.bucket,
                    file_path=imported_file.file_path,
                    file_name=imported_file.file_name,
                    file_ext=imported_file.file_ext,
                    file_type=imported_file.file_type,
                    file_size=imported_file.file_size,
                    source_file=imported_file.source_file,
                    created_at=imported_file.created_at,
                    updated_at=imported_file.updated_at
                )
                imported_files.append(file_response)

            except Exception as e:
                error_msg = f"Failed to import file {file_id}: {str(e)}"
                logger.error(f"[API_IMPORT] Failed to import file - file_id: {file_id}, error: {error_msg}", exc_info=True)
                errors.append({"file_id": file_id, "error": error_msg})
                continue

        if not imported_files:
            raise AppError("Failed to import any files", status_code=HTTP_400_BAD_REQUEST)

        return created(
            data=imported_files,
            message=f"Imported {len(imported_files)} file(s) successfully. {len(errors)} failed." if errors else f"Imported {len(imported_files)} file(s) successfully"
        )

    except AppError:
        raise
    except Exception as e:
        logger.error(f"[API_IMPORT] Unexpected error: {str(e)}", exc_info=True)
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)


@router.post(
    "/import-sheet-url",
    response_model=ApiResponse[FileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Import Sheet from URL",
    description="Import a Google Sheet from URL to MinIO storage. Sets source_file to 'drive'."
)
@invalidate_cache("files")
async def import_sheet_from_url(
    request: ImportSheetUrlRequest,
    current_user: dict = Depends(verify_token)
):
    """
    Import a Google Sheet from URL to MinIO storage

    This endpoint extracts the sheet ID from a Google Sheets URL, exports it to Excel format,
    uploads it to MinIO, and saves metadata to the database with source_file='drive'.

    **Request Body:**
    - **sheet_url**: Google Sheet URL (various formats supported)

    **Response:**
    - Imported file with metadata (source_file='drive')
    """
    try:
        # Extract sheet ID from URL
        patterns = [
            r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
            r'/([a-zA-Z0-9-_]{44})',  # Standard sheet ID length
        ]

        sheet_id = None
        for pattern in patterns:
            match = re.search(pattern, request.sheet_url)
            if match:
                sheet_id = match.group(1)
                break

        if not sheet_id:
            raise AppError("Could not extract sheet ID from URL", status_code=HTTP_400_BAD_REQUEST)

        # Get user and access token
        clerk_id = current_user.get("sub")
        user = await user_service.crud.get_by_clerk_id(clerk_id)
        if not user or not user.minio_secret_key:
            raise AppError("User not found", status_code=HTTP_400_BAD_REQUEST)

        user_id = str(user.id)

        with Clerk(bearer_auth=settings.CLERK_SECRET_KEY) as clerk:
            res = clerk.users.get_o_auth_access_token(
                user_id=clerk_id,
                provider="oauth_google"
            )
            access_token = res[0].token

        # Initialize file service
        file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

        # Get file info to get the name
        file_info = GoogleServices.get_file_info(access_token, sheet_id)
        file_name = file_info.get("name", "sheet")

        # Import file (source_file will be set to "drive" in import_from_drive)
        imported_file = await file_service.import_from_drive(
            user_id=user_id,
            file_id=sheet_id,
            file_name=file_name,
            file_type="sheet",
            access_token=access_token
        )

        logger.info(f"[API_IMPORT] Successfully imported sheet from URL - file_id: {imported_file.id}, name: {file_name}, source: {imported_file.source_file}")

        # Convert to FileResponse
        file_response = FileResponse(
            id=str(imported_file.id),
            owner_id=imported_file.owner_id,
            bucket=imported_file.bucket,
            file_path=imported_file.file_path,
            file_name=imported_file.file_name,
            file_ext=imported_file.file_ext,
            file_type=imported_file.file_type,
            file_size=imported_file.file_size,
            source_file=imported_file.source_file,
            created_at=imported_file.created_at,
            updated_at=imported_file.updated_at
        )

        return created(
            data=file_response,
            message="Sheet imported successfully"
        )

    except AppError:
        raise
    except Exception as e:
        logger.error(f"[API_IMPORT] Unexpected error importing sheet from URL: {str(e)}", exc_info=True)
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)
