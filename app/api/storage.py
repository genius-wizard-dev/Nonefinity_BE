from fastapi import APIRouter,  UploadFile, HTTPException
from app.services import StorageService, user_service
from app.schemas.response import ApiResponse
from starlette.status import HTTP_400_BAD_REQUEST
from app.core.exceptions import AppError
from app.schemas.file import FileResponse
from app.utils.api_response import created, ok
import mimetypes
router = APIRouter()

@router.post("/upload/file", response_model=ApiResponse[FileResponse])
async def upload_file(file: UploadFile):

  user_id = "68bbed17a5cc02a35ac0e0fd"
  user = await user_service.crud.get_by_id(user_id)
  if not user or not user.minio_secret_key:
    raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

  storage_service = StorageService(access_key=user_id, secret_key=user.minio_secret_key)

  result = await storage_service.upload_file(user_id=user_id, file=file)
  if not result:
    raise AppError("File upload failed", status_code=HTTP_400_BAD_REQUEST)

  return created(result, message="File uploaded successfully")


@router.delete("/delete/file/{file_id}", response_model=ApiResponse[bool])
async def delete_file(file_id: str):
    user_id = "68bbed17a5cc02a35ac0e0fd"
    user = await user_service.crud.get_by_id(user_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    storage_service = StorageService(access_key=user_id, secret_key=user.minio_secret_key)

    result = await storage_service.delete_file(user_id=user_id, file_id=file_id)
    if not result:
        raise AppError("File deletion failed", status_code=HTTP_400_BAD_REQUEST)

    return ok(message="File deleted successfully")


@router.get("/download/file/{file_id}", response_model=ApiResponse[str])
async def download_file(file_id: str):
    user_id = "68bbed17a5cc02a35ac0e0fd"
    user = await user_service.crud.get_by_id(user_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    storage_service = StorageService(access_key=user_id, secret_key=user.minio_secret_key)

    file = await storage_service.crud.get_by_id(file_id)
    if not file:
        raise AppError("File not found", status_code=HTTP_400_BAD_REQUEST)

    url = storage_service._minio_service.get_url(bucket_name=file.bucket, object_name=file.object_name)
    if not url:
        raise AppError("Failed to get file URL", status_code=HTTP_400_BAD_REQUEST)

    return ok(data=url, message="File URL retrieved successfully")


@router.get("/list/files", response_model=ApiResponse[list[FileResponse]])
async def list_files():
    user_id = "68bbed17a5cc02a35ac0e0fd"
    user = await user_service.crud.get_by_id(user_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    storage_service = StorageService(access_key=user_id, secret_key=user.minio_secret_key)

    files = await storage_service.list_files(user_id=user_id)
    if files is None:
        raise AppError("Failed to list files", status_code=HTTP_400_BAD_REQUEST)

    return ok(data=files, message="Files listed successfully")
