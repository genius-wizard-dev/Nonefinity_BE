from app.services.minio_client_service import MinIOClientService
from fastapi import UploadFile
from app.schemas.file import FileCreate, FileUpdate
from app.crud.file import FileCRUD
from app.core.exceptions import AppError
from app.utils import get_logger
from typing import Optional, List
import mimetypes
import uuid
import os

logger = get_logger(__name__)

class FileService:
    def __init__(self, access_key: str, secret_key: str, crud: Optional[FileCRUD] = None):
        self._minio_client = MinIOClientService(access_key=access_key, secret_key=secret_key)
        self.crud = crud or FileCRUD()

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        if not original_filename:
            return str(uuid.uuid4())

        name, ext = os.path.splitext(original_filename)
        unique_name = str(uuid.uuid4())
        return unique_name, ext


    async def upload_file(self, user_id: str, file: UploadFile) -> Optional[FileCreate]:
        """Upload file with comprehensive error handling and rollback"""
        file_create = None
        object_name = None

        try:
            logger.info(f"Starting file upload for user {user_id}, file: {file.filename}")

            # Validate file
            if not file.filename:
                raise AppError("File name is required")

            if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
                raise AppError("File size exceeds 10MB limit")

            # Get root folder and generate unique filename
            root_folder = "raw"
            original_name, original_ext = os.path.splitext(file.filename)
            unique_filename, file_ext = self._generate_unique_filename(file.filename)

            # Create object path: root_folder/unique_filename.ext
            object_name = f"{root_folder}/{unique_filename}{file_ext}"

            # Determine content type
            content_type = file.content_type
            if content_type == "application/octet-stream" and file.filename:
                guessed_type, _ = mimetypes.guess_type(file.filename)
                if guessed_type:
                    content_type = guessed_type


            # Create database record first
            file_info = FileCreate(
                bucket=user_id,
                file_name=original_name,
                file_ext=file_ext,
                object_name=object_name,
                file_size=file.size,
                file_type=content_type,
                owner_id=user_id
            )

            file_create = await self.crud.create(obj_in=file_info)
            logger.info(f"Created database record for file: {file_create.id}")

            # Upload to MinIO
            upload_success = self._minio_client.upload_file(
                bucket_name=user_id,
                file=file,
                object_name=object_name
            )

            if not upload_success:
                logger.error(f"MinIO upload failed for file: {object_name}")
                raise AppError("Failed to upload file to storage")

            # Generate presigned URL and update record
            url = self._minio_client.get_url(bucket_name=user_id, object_name=object_name)
            if url:
                update_data = FileUpdate(url=url)
                await self.crud.update(file_create, obj_in=update_data)

            logger.info(f"File upload completed successfully: {file_create.id}")
            return file_create

        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")

            # Rollback operations
            if file_create:
                try:
                    await self.crud.delete(file_create)  # Hard delete
                    logger.info(f"Rolled back database record: {file_create.id}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup database record: {cleanup_error}")

            if object_name:
                try:
                    self._minio_client.delete_file(user_id=user_id, file_name=object_name)
                    logger.info(f"Rolled back MinIO object: {object_name}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup MinIO object: {cleanup_error}")

            if isinstance(e, AppError):
                raise e
            else:
                raise AppError(f"Upload failed: {str(e)}")

    async def delete_file(self, user_id: str, file_id: str) -> bool:
        """Delete file permanently from both MongoDB and MinIO"""
        try:
            logger.info(f"Starting file deletion for user {user_id}, file_id: {file_id}")

            file = await self.crud.get_by_id(file_id)
            if not file:
                logger.warning(f"File not found: {file_id}")
                raise AppError("File not found")

            if file.owner_id != user_id:
                logger.warning(f"Unauthorized file deletion attempt: {file_id} by {user_id}")
                raise AppError("Unauthorized: Cannot delete file")

            # Delete from MinIO first
            minio_deleted = self._minio_client.delete_file(user_id=user_id, file_name=file.object_name)
            if not minio_deleted:
                logger.error(f"Failed to delete file from MinIO: {file.object_name}")
                raise AppError("Failed to delete file from storage")

            # Delete from database (hard delete)
            await self.crud.delete(file)

            logger.info(f"File deleted successfully: {file_id}")
            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            raise AppError(f"Deletion failed: {str(e)}")

    async def rename_file(self, user_id: str, file_id: str, new_name: str) -> Optional[FileCreate]:
        """Rename file (only update database, keep MinIO object unchanged)"""
        try:
            logger.info(f"Renaming file {file_id} to {new_name} for user {user_id}")

            file = await self.crud.get_by_id(file_id)
            if not file:
                raise AppError("File not found")

            if file.owner_id != user_id:
                raise AppError("Unauthorized: Cannot rename file")

            # Update only file_name in database
            update_data = FileUpdate(file_name=new_name)
            updated_file = await self.crud.update(file, obj_in=update_data)

            logger.info(f"File renamed successfully: {file_id}")
            return updated_file

        except AppError:
            raise
        except Exception as e:
            logger.error(f"File rename failed: {str(e)}")
            raise AppError(f"Rename failed: {str(e)}")

    async def list_files(self, user_id: str) -> List[FileCreate]:
        """List all files for user"""
        filter_dict = {"owner_id": user_id}
        files = await self.crud.list(filter_=filter_dict)
        return files



