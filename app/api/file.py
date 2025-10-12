from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from app.services import FileService, user_service
from app.schemas.response import ApiResponse, ApiError
from starlette.status import HTTP_400_BAD_REQUEST
from app.core.exceptions import AppError
from app.schemas.file import (
    FileResponse, FileUpdate, BatchDeleteRequest, UploadUrlRequest,
    UploadUrlResponse, FileMetadataRequest
)
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from typing import Optional, List

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
async def save_file_metadata(
    request: FileMetadataRequest,
    current_user = Depends(verify_token)
):
    """
    Save file metadata after upload to MinIO

    This endpoint saves file metadata to the database after a file has been successfully
    uploaded to MinIO storage using the presigned URL.

    **Parameters:**
    - **object_name**: Object name in MinIO storage (from upload URL response)
    - **file_name**: Original file name
    - **file_type**: MIME type of the file
    - **file_size**: File size in bytes (optional)

    **Returns:**
    - Complete file information including database ID and timestamps

    **Example:**
    ```json
    {
        "object_name": "raw/user123/document.pdf",
        "file_name": "my-document.pdf",
        "file_type": "application/pdf",
        "file_size": 1024000
    }
    ```
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    try:
        result = await file_service.save_file_metadata(
            user_id=user_id,
            object_name=request.object_name,
            file_name=request.file_name,
            file_type=request.file_type,
            file_size=request.file_size
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
async def delete_file(
    file_id: str = Path(..., description="File ID to delete"),
    current_user = Depends(verify_token)
):
    """
    Delete file from storage and database

    This endpoint permanently deletes a file from both MinIO storage and the database.
    The operation cannot be undone.

    **Parameters:**
    - **file_id**: Unique identifier of the file to delete

    **Returns:**
    - Success status indicating whether the deletion was successful

    **Note:**
    - This operation is irreversible
    - File will be removed from both storage and database
    """
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
    """
    List all files for the current user

    This endpoint retrieves a list of all files owned by the authenticated user.
    Files are returned with complete metadata including size, type, and timestamps.

    **Returns:**
    - List of file objects with complete metadata
    - Each file includes ID, name, type, size, and timestamps

    **Example Response:**
    ```json
    {
        "success": true,
        "message": "Files listed successfully",
        "data": [
            {
                "id": "507f1f77bcf86cd799439011",
                "file_name": "document.pdf",
                "file_type": "application/pdf",
                "file_size": 1024000,
                "created_at": "2024-01-15T10:30:00Z"
            }
        ]
    }
    ```
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    files = await file_service.list_files(user_id=user_id)
    if files is None:
        raise AppError("Failed to list files", status_code=HTTP_400_BAD_REQUEST)

    return ok(data=files, message="Files listed successfully")

@router.put("/rename/{file_id}", response_model=ApiResponse[FileResponse])
async def rename_file(file_id: str, new_name: str, current_user = Depends(verify_token)):
    """Rename file in raw/ folder

    Args:
        file_id: File ID
        new_name: New name
        current_user: Current user
    """
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
async def get_download_url(file_id: str, current_user = Depends(verify_token)):
    """Get presigned download URL for file from raw/ folder

    Args:
        file_id: File ID
        current_user: Current user
    """
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


    return ok(data=files, message="Search completed successfully")

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

    # Group by file type
    file_types = {}
    for file in all_files:
        file_type = file.file_type.split('/')[0] if file.file_type else 'unknown'
        file_types[file_type] = file_types.get(file_type, 0) + 1

    stats = {
        "total_files": total_files,
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
        "file_types": file_types
    }

    return ok(data=stats, message="Statistics retrieved successfully")

@router.get("/types", response_model=ApiResponse[List[str]])
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
async def get_list_allow_convert(current_user = Depends(verify_token)):
    """Get list of files that are allowed to be converted to dataset"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    files = await file_service.get_list_allow_convert(user_id)

    return ok(data=files, message="List of files that are allowed to be converted to dataset retrieved successfully")


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

    return ok(data=files, message="List of files that are allowed to be extracted retrieved successfully")
