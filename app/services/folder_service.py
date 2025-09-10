from app.crud.folder import FolderCRUD
from app.services.minio_client_service import MinIOClientService
from app.schemas import FolderCreate, FolderResponse, FolderUpdate

from app.core.exceptions import AppError
from app.utils import get_logger
from starlette.status import HTTP_400_BAD_REQUEST
from typing import List, Optional

logger = get_logger(__name__)

class FolderService:
    def __init__(self, access_key: str, secret_key: str, crud: Optional[FolderCRUD] = None):
        self.crud = crud or FolderCRUD()
        self._minio_client = MinIOClientService(access_key=access_key, secret_key=secret_key)

    async def create_folder(self, user_id: str, folder_name: str, parent_path: str) -> FolderResponse:
        """Create folder with comprehensive validation and error handling"""
        minio_folder_path = None

        try:
            logger.info(f"Creating folder for user {user_id}: {folder_name}")

            # Validate folder name
            if not folder_name or not folder_name.strip():
                raise AppError("Folder name is required")

            # Sanitize folder name (remove invalid characters)
            import re
            sanitized_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name.strip())
            if sanitized_name != folder_name:
                logger.warning(f"Folder name sanitized: {folder_name} -> {sanitized_name}")

            # Create full folder path
            if parent_path == "/":
                folder_path = f"/{sanitized_name}"
            else:
                # Ensure parent path starts with /
                parent_path = parent_path
                if not parent_path.startswith('/'):
                    parent_path = '/' + parent_path
                folder_path = f"{parent_path.rstrip('/')}/{sanitized_name}"

            # Check if folder already exists in database
            existing = await self.crud.get_by_path(user_id, folder_path)
            if existing and not existing.deleted_at:
                raise AppError("Folder already exists")

            # Validate parent folder exists (if not root)
            if parent_path != "/":
                parent_folder = await self.crud.get_by_path(user_id, parent_path)
                if not parent_folder:
                    raise AppError("Parent folder does not exist")

            # Create folder in MinIO
            minio_folder_path = folder_path.lstrip('/') + '/' if folder_path != '/' else ''
            folder_created = self._minio_client.create_folder(bucket_name=user_id, folder_path=minio_folder_path)
            if not folder_created:
                logger.error(f"Failed to create folder in MinIO: {minio_folder_path}")
                raise AppError("Failed to create folder in storage")

            # Create folder using internal schema
            folder_create = FolderCreate(
                owner_id=user_id,
                folder_name=sanitized_name,
                folder_path=folder_path,
                parent_path=parent_path
            )

            folder = await self.crud.create(obj_in=folder_create)

            logger.info(f"Folder created successfully: {folder.id}")
            return folder

        except AppError:
            # Rollback MinIO folder creation if it was created
            if minio_folder_path:
                try:
                    self._minio_client.delete_folder(bucket_name=user_id, folder_path=minio_folder_path)
                    logger.info(f"Rolled back MinIO folder: {minio_folder_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup MinIO folder: {cleanup_error}")
            raise
        except Exception as e:
            # Rollback MinIO folder creation if it was created
            if minio_folder_path:
                try:
                    self._minio_client.delete_folder(bucket_name=user_id, folder_path=minio_folder_path)
                    logger.info(f"Rolled back MinIO folder: {minio_folder_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup MinIO folder: {cleanup_error}")

            logger.error(f"Folder creation failed: {str(e)}")
            raise AppError(f"Failed to create folder: {str(e)}")

    async def delete_folder(self, user_id: str, folder_id: str) -> bool:
        folder = await self.crud.get_by_id(folder_id)
        if not folder or folder.owner_id != user_id:
            raise AppError("Folder not found", status_code=HTTP_400_BAD_REQUEST)

        # Check if folder has children
        children = await self.crud.get_children(user_id, folder.folder_path)
        if children:
            raise AppError("Cannot delete folder with subfolders", status_code=HTTP_400_BAD_REQUEST)

        # Delete from MinIO
        minio_folder_path = folder.folder_path.lstrip('/') + '/' if folder.folder_path != '/' else ''
        minio_deleted = self._minio_client.delete_folder(bucket_name=user_id, folder_path=minio_folder_path)
        if not minio_deleted:
            raise AppError("Failed to delete folder from storage", status_code=HTTP_400_BAD_REQUEST)

        try:
            await self.crud.delete(folder)
            return True
        except Exception:
            # Note: MinIO folder already deleted, consider logging this for cleanup
            raise

    async def list_folders(self, user_id: str, parent_path: str = "/") -> List[FolderResponse]:
        folders = await self.crud.get_children(user_id, parent_path)
        return folders

    async def rename_folder(self, user_id: str, folder_id: str, new_name: str) -> FolderResponse:
        folder = await self.crud.get_by_id(folder_id)
        if not folder or folder.owner_id != user_id:
            raise AppError("Folder not found", status_code=HTTP_400_BAD_REQUEST)

        # Update folder path
        old_path = folder.folder_path
        if folder.parent_path == "/":
            new_path = f"/{new_name}"
        else:
            new_path = f"{folder.parent_path.rstrip('/')}/{new_name}"

        # Check if new path already exists
        existing = await self.crud.get_by_path(user_id, new_path)
        if existing:
            raise AppError("Folder with this name already exists", status_code=HTTP_400_BAD_REQUEST)

        # Rename in MinIO
        old_minio_path = old_path.lstrip('/') + '/' if old_path != '/' else ''
        new_minio_path = new_path.lstrip('/') + '/' if new_path != '/' else ''

        renamed = self._minio_client.rename_folder(bucket_name=user_id, old_path=old_minio_path, new_path=new_minio_path)
        if not renamed:
            raise AppError("Failed to rename folder in storage", status_code=HTTP_400_BAD_REQUEST)

        try:
            # Update folder
            folder.folder_name = new_name
            folder.folder_path = new_path
            await folder.save()
            return folder
        except Exception:
            # Rollback: rename back in MinIO
            self._minio_client.rename_folder(bucket_name=user_id, old_path=new_minio_path, new_path=old_minio_path)
            raise

    async def move_folder(self, user_id: str, folder_id: str, new_parent_path: str) -> FolderResponse:
        folder = await self.crud.get_by_id(folder_id)
        if not folder or folder.owner_id != user_id:
            raise AppError("Folder not found", status_code=HTTP_400_BAD_REQUEST)

        # Calculate new folder path
        old_path = folder.folder_path
        if new_parent_path == "/":
            new_folder_path = f"/{folder.folder_name}"
        else:
            new_folder_path = f"{new_parent_path.rstrip('/')}/{folder.folder_name}"

        # Check if new path already exists
        existing = await self.crud.get_by_path(user_id, new_folder_path)
        if existing:
            raise AppError("Folder already exists in destination", status_code=HTTP_400_BAD_REQUEST)

        # Move in MinIO
        old_minio_path = old_path.lstrip('/') + '/' if old_path != '/' else ''
        new_minio_path = new_folder_path.lstrip('/') + '/' if new_folder_path != '/' else ''

        moved = self._minio_client.move_folder(bucket_name=user_id, old_path=old_minio_path, new_path=new_minio_path)
        if not moved:
            raise AppError("Failed to move folder in storage", status_code=HTTP_400_BAD_REQUEST)

        try:
            # Update folder
            folder.parent_path = new_parent_path
            folder.folder_path = new_folder_path
            await folder.save()
            return folder
        except Exception:
            # Rollback: move back in MinIO
            self._minio_client.move_folder(bucket_name=user_id, old_path=new_minio_path, new_path=old_minio_path)
            raise

    async def check_folder_has_files(self, user_id: str, folder_path: str) -> bool:
        """Check if folder contains any files"""
        from app.crud.file import FileCRUD
        file_crud = FileCRUD()
        files = await file_crud.list(filter_={"owner_id": user_id, "folder_path": folder_path}, include_deleted=False)
        return len(files) > 0
