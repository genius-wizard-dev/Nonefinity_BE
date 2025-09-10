from fastapi import APIRouter, Depends, UploadFile, HTTPException, Query
from app.services import FileService, user_service
from app.schemas.response import ApiResponse
from starlette.status import HTTP_400_BAD_REQUEST
from app.core.exceptions import AppError
from app.schemas.file import FileResponse, FileUpdate
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from typing import Optional, List

router = APIRouter()

@router.post("/upload", response_model=ApiResponse[FileResponse])
async def upload_file(file: UploadFile, folder_path: str = "/", current_user = Depends(verify_token)):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")
    user_id = str(user.id)
    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    result = await file_service.upload_file(user_id=user_id, file=file, folder_path=folder_path)
    if not result:
        raise AppError("File upload failed", status_code=HTTP_400_BAD_REQUEST)

    return created(result, message="File uploaded successfully")

@router.delete("/{file_id}", response_model=ApiResponse[bool])
async def delete_file(file_id: str, current_user = Depends(verify_token)):
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

@router.get("/download/{file_id}", response_model=ApiResponse[str])
async def download_file(file_id: str, current_user = Depends(verify_token)):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    file = await file_service.crud.get_by_id(file_id)
    if not file or file.owner_id != user_id:
        raise AppError("File not found", status_code=HTTP_400_BAD_REQUEST)

    url = file_service._minio_service.get_url(bucket_name=file.bucket, object_name=file.object_name)
    if not url:
        raise AppError("Failed to get file URL", status_code=HTTP_400_BAD_REQUEST)

    return ok(data=url, message="File URL retrieved successfully")

@router.get("/list", response_model=ApiResponse[list[FileResponse]])
async def list_files(folder_path: str = None, current_user = Depends(verify_token)):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    files = await file_service.list_files(user_id=user_id, folder_path=folder_path)
    if files is None:
        raise AppError("Failed to list files", status_code=HTTP_400_BAD_REQUEST)

    return ok(data=files, message="Files listed successfully")

@router.put("/rename/{file_id}", response_model=ApiResponse[FileResponse])
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

@router.put("/move/{file_id}", response_model=ApiResponse[FileResponse])
async def move_file(file_id: str, new_folder_path: str, current_user = Depends(verify_token)):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)
    file = await file_service.crud.get_by_id(file_id)
    if not file or file.owner_id != user_id:
        raise AppError("File not found", status_code=HTTP_400_BAD_REQUEST)

    update_data = FileUpdate(folder_path=new_folder_path)
    updated_file = await file_service.crud.update(file, obj_in=update_data)
    return ok(data=updated_file, message="File moved successfully")

@router.get("/search", response_model=ApiResponse[List[FileResponse]])
async def search_files(
    q: str = Query(..., description="Search term"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    folder_path: Optional[str] = Query(None, description="Search within specific folder"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    current_user = Depends(verify_token)
):
    """Search files by name with optional filters"""
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

    # Filter by folder if specified
    if folder_path:
        files = [f for f in files if f.folder_path == folder_path]

    return ok(data=files, message="Search completed successfully")

@router.get("/stats", response_model=ApiResponse[dict])
async def get_file_stats(
    folder_path: Optional[str] = Query(None, description="Get stats for specific folder"),
    current_user = Depends(verify_token)
):
    """Get file statistics for user or specific folder"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    if folder_path:
        total_files = await file_service.crud.count_files_in_folder(user_id, folder_path)
        total_size = await file_service.crud.get_total_size_in_folder(user_id, folder_path)
        stats = {
            "folder_path": folder_path,
            "total_files": total_files,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0
        }
    else:
        # Get overall stats for user
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
    """Get all unique file types for the user"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

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

@router.post("/copy/{file_id}", response_model=ApiResponse[FileResponse])
async def copy_file(
    file_id: str,
    new_folder_path: str,
    new_name: Optional[str] = None,
    current_user = Depends(verify_token)
):
    """Copy file to a new location"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    try:
        copied_file = await file_service.copy_file(user_id, file_id, new_folder_path, new_name)
        if not copied_file:
            raise AppError("Failed to copy file", status_code=HTTP_400_BAD_REQUEST)

        return created(copied_file, message="File copied successfully")
    except AppError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/batch/delete", response_model=ApiResponse[dict])
async def batch_delete_files(
    file_ids: List[str],
    current_user = Depends(verify_token)
):
    """Delete multiple files at once"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    results = {"successful": [], "failed": []}

    for file_id in file_ids:
        try:
            success = await file_service.delete_file(user_id, file_id)
            if success:
                results["successful"].append(file_id)
            else:
                results["failed"].append({"file_id": file_id, "error": "Deletion failed"})
        except Exception as e:
            results["failed"].append({"file_id": file_id, "error": str(e)})

    return ok(data=results, message=f"Batch deletion completed. {len(results['successful'])} successful, {len(results['failed'])} failed")

@router.post("/batch/move", response_model=ApiResponse[dict])
async def batch_move_files(
    file_ids: List[str],
    new_folder_path: str,
    current_user = Depends(verify_token)
):
    """Move multiple files to a new folder"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    results = {"successful": [], "failed": []}

    for file_id in file_ids:
        try:
            success = await file_service.move_file_to_folder(user_id, file_id, new_folder_path)
            if success:
                results["successful"].append(file_id)
            else:
                results["failed"].append({"file_id": file_id, "error": "Move failed"})
        except Exception as e:
            results["failed"].append({"file_id": file_id, "error": str(e)})

    return ok(data=results, message=f"Batch move completed. {len(results['successful'])} successful, {len(results['failed'])} failed")
