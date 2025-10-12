from fastapi import APIRouter, Depends, HTTPException, Query
from app.services import FileService, user_service
from app.schemas.response import ApiResponse
from starlette.status import HTTP_400_BAD_REQUEST
from app.core.exceptions import AppError
from app.schemas.file import FileResponse, FileUpdate, BatchDeleteRequest, UploadUrlRequest, UploadUrlResponse, FileMetadataRequest
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from app.utils.cache_decorator import cache_list, invalidate_cache
from typing import Optional, List

router = APIRouter()

@router.post("/upload-url", response_model=ApiResponse[UploadUrlResponse])
async def get_upload_url(request: UploadUrlRequest, current_user = Depends(verify_token)):
    """Get presigned upload URL for file upload

    Args:
        request: Upload URL request with file metadata
        current_user: Current user
    """
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

@router.post("/upload", response_model=ApiResponse[FileResponse])
@invalidate_cache("files")
async def save_file_metadata(request: FileMetadataRequest, current_user = Depends(verify_token)):
    """Save file metadata after upload to MinIO

    Args:
        request: File metadata after upload
        current_user: Current user
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

@router.delete("/{file_id}", response_model=ApiResponse[bool])
@invalidate_cache("files")
async def delete_file(file_id: str, current_user = Depends(verify_token)):
    """Delete file from raw/ folder

    Args:
        file_id: File ID
        current_user: Current user
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


@router.get("/list", response_model=ApiResponse[list[FileResponse]])
@cache_list("files", ttl=300)  # Cache for 5 minutes
async def list_files(current_user = Depends(verify_token)):
    """List all files in raw/ folder

    Args:
        current_user: Current user
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
@invalidate_cache("files")
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
