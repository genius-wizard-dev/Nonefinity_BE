from fastapi import APIRouter, Depends, HTTPException, Query, Body
from app.services import user_service
from app.services import FolderService, FileService
from app.schemas.response import ApiResponse
from starlette.status import HTTP_400_BAD_REQUEST
from app.core.exceptions import AppError
from app.schemas import FolderResponse, FolderCreate
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from typing import Optional, List

router = APIRouter()

@router.post("/create", response_model=ApiResponse[FolderResponse])
async def create_folder(
    folder_name: str = Body(...),
    parent_path: str = Body("/"),
    current_user = Depends(verify_token)
):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)
    folder = await folder_service.create_folder(user_id, folder_name, parent_path)
    return created(folder, message="Folder created successfully")

@router.delete("/{folder_id}", response_model=ApiResponse[bool])
async def delete_folder(
    folder_id: str,
    current_user = Depends(verify_token)
):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)

    # Get folder to check if it has files
    folder = await folder_service.crud.get_by_id(folder_id)
    if not folder or folder.owner_id != user_id:
        raise AppError("Folder not found", status_code=HTTP_400_BAD_REQUEST)

    # Check if folder has files using file service
    has_files = await folder_service.check_folder_has_files(user_id, folder.folder_path)
    if has_files:
        raise AppError("Cannot delete folder with files", status_code=HTTP_400_BAD_REQUEST)

    await folder_service.delete_folder(user_id, folder_id)
    return ok(message="Folder deleted successfully")

@router.get("/list", response_model=ApiResponse[list[FolderResponse]])
async def list_folders(
    parent_path: str = "/",
    current_user = Depends(verify_token)
):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)
    folders = await folder_service.list_folders(user_id, parent_path)
    return ok(data=folders, message="Folders listed successfully")

@router.put("/rename/{folder_id}", response_model=ApiResponse[FolderResponse])
async def rename_folder(
    folder_id: str,
    new_name: str = Body(...),
    current_user = Depends(verify_token)
):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)
    folder = await folder_service.rename_folder(user_id, folder_id, new_name)
    return ok(data=folder, message="Folder renamed successfully")

@router.put("/move/{folder_id}", response_model=ApiResponse[FolderResponse])
async def move_folder(
    folder_id: str,
    new_parent_path: str = Body(...),
    current_user = Depends(verify_token)
):
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)
    folder = await folder_service.move_folder(user_id, folder_id, new_parent_path)
    return ok(data=folder, message="Folder moved successfully")

@router.get("/files", response_model=ApiResponse[list])
async def list_files_in_folder(
    folder_path: str = "/",
    current_user = Depends(verify_token)
):
    """List all files in a specific folder"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)
    files = await file_service.list_files_in_folder(user_id, folder_path)
    return ok(data=files, message="Files listed successfully")

@router.get("/tree", response_model=ApiResponse[List[dict]])
async def get_folder_tree(
    root_path: str = Query("/", description="Root path to start tree from"),
    current_user = Depends(verify_token)
):
    """Get folder tree structure"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)
    tree = await folder_service.crud.get_folder_tree(user_id, root_path)
    return ok(data=tree, message="Folder tree retrieved successfully")

@router.get("/search", response_model=ApiResponse[List[FolderResponse]])
async def search_folders(
    q: str = Query(..., description="Search term"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    current_user = Depends(verify_token)
):
    """Search folders by name"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)
    folders = await folder_service.crud.search_folders_by_name(user_id, q, limit)
    return ok(data=folders, message="Search completed successfully")

@router.get("/stats", response_model=ApiResponse[dict])
async def get_folder_stats(
    folder_path: str = Query("/", description="Folder path to get stats for"),
    current_user = Depends(verify_token)
):
    """Get folder statistics including subfolders and files count"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)
    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    # Count direct subfolders
    subfolder_count = await folder_service.crud.count_subfolders(user_id, folder_path)

    # Count files in this folder
    file_count = await file_service.crud.count_files_in_folder(user_id, folder_path)

    # Get total size of files in this folder
    total_size = await file_service.crud.get_total_size_in_folder(user_id, folder_path)

    stats = {
        "folder_path": folder_path,
        "subfolders_count": subfolder_count,
        "files_count": file_count,
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0
    }

    return ok(data=stats, message="Folder statistics retrieved successfully")

@router.get("/content", response_model=ApiResponse[dict])
async def get_folder_content(
    folder_path: str = Query("/", description="Folder path to get content for"),
    current_user = Depends(verify_token)
):
    """Get complete folder content (subfolders + files) for UI rendering"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    user_id = str(user.id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    folder_service = FolderService(access_key=user_id, secret_key=user.minio_secret_key)
    file_service = FileService(access_key=user_id, secret_key=user.minio_secret_key)

    # Get subfolders
    subfolders = await folder_service.crud.get_children(user_id, folder_path)

    # Get files in this folder
    files = await file_service.crud.get_files_in_folder(user_id, folder_path)

    content = {
        "folder_path": folder_path,
        "subfolders": subfolders,
        "files": files,
        "total_items": len(subfolders) + len(files)
    }

    return ok(data=content, message="Folder content retrieved successfully")
