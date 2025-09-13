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
        self.access_key = access_key
        self.secret_key = secret_key

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        if not original_filename:
            return str(uuid.uuid4())[:6]

        name, ext = os.path.splitext(original_filename)
        # Generate 6-character random string instead of long UUID
        unique_name = str(uuid.uuid4()).replace('-', '')[:6]
        return unique_name, ext


    async def upload_file(self, user_id: str, file: UploadFile) -> Optional[FileCreate]:
        """Upload file to raw/ folder only - simplified version"""
        file_create = None
        object_name = None

        try:
            logger.info(f"Starting file upload for user {user_id}, file: {file.filename}")

            # Validate file
            if not file.filename:
                raise AppError("File name is required")

            if file.size and file.size > 100 * 1024 * 1024:  # 100MB limit
                raise AppError("File size exceeds 100MB limit")

            # Get root folder and generate unique filename
            root_folder = "raw"
            original_name, original_ext = os.path.splitext(file.filename)
            unique_filename, file_ext = self._generate_unique_filename(file.filename)

            # Create file path: raw/unique_filename.ext
            file_path = f"{root_folder}/{unique_filename}{file_ext}"

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
                file_path=file_path,
                file_size=file.size,
                file_type=content_type,
                owner_id=user_id
            )

            file_create = await self.crud.create(obj_in=file_info)
            logger.info(f"Created database record for file: {file_create.id}")

            # Upload file to MinIO
            upload_success = self._minio_client.upload_file(
                bucket_name=user_id,
                file=file,
                object_name=file_path
            )

            if not upload_success:
                logger.error(f"MinIO upload failed for file: {file_path}")
                raise AppError("Failed to upload file to storage")

            # Generate presigned URL and update record
            url = self._minio_client.get_url(bucket_name=user_id, object_name=file_path)
            if url:
                final_update = FileUpdate(url=url)
                await self.crud.update(file_create, obj_in=final_update)

            logger.info(f"File upload completed successfully: {file_create.id}")
            return file_create

        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")

            # Simple rollback operations
            rollback_errors = []

            # 1. Rollback original file from MinIO
            if file_path:
                try:
                    file_deleted = self._minio_client.delete_file(bucket_name=user_id, file_name=file_path)
                    if file_deleted:
                        logger.info(f"Rolled back MinIO file: {file_path}")
                    else:
                        error_msg = f"Failed to delete original file: {file_path}"
                        logger.warning(error_msg)
                        rollback_errors.append(error_msg)
                except Exception as cleanup_error:
                    error_msg = f"Failed to cleanup MinIO file: {cleanup_error}"
                    logger.error(error_msg)
                    rollback_errors.append(error_msg)

            # 2. Rollback database record
            if file_create:
                try:
                    await self.crud.delete(file_create, soft_delete=False)  # Hard delete
                    logger.info(f"Rolled back database record: {file_create.id}")
                except Exception as cleanup_error:
                    error_msg = f"Failed to cleanup database record: {cleanup_error}"
                    logger.error(error_msg)
                    rollback_errors.append(error_msg)

            # Log rollback summary
            if rollback_errors:
                logger.error(f"Rollback completed with errors: {'; '.join(rollback_errors)}")
            else:
                logger.info("Complete rollback successful")

            # Re-raise original exception
            if isinstance(e, AppError):
                raise e
            else:
                raise AppError(f"Upload failed: {str(e)}")

    async def delete_file(self, user_id: str, file_id: str) -> bool:
        """Delete file permanently from both MongoDB and MinIO - simplified version

        Args:
            user_id: User ID
            file_id: File ID
        """
        deletion_errors = []

        try:
            logger.info(f"Starting file deletion for user {user_id}, file_id: {file_id}")

            file = await self.crud.get_by_id(file_id)
            if not file:
                logger.warning(f"File not found: {file_id}")
                raise AppError("File not found")

            if file.owner_id != user_id:
                logger.warning(f"Unauthorized file deletion attempt: {file_id} by {user_id}")
                raise AppError("Unauthorized: Cannot delete file")

            # Delete file from MinIO
            try:
                main_file_deleted = self._minio_client.delete_file(bucket_name=user_id, file_name=file.file_path)
                if main_file_deleted:
                    logger.info(f"Deleted main file from MinIO: {file.file_path}")
                else:
                    error_msg = f"Failed to delete main file from MinIO: {file.file_path}"
                    logger.error(error_msg)
                    deletion_errors.append(error_msg)
            except Exception as e:
                error_msg = f"Failed to delete main file: {str(e)}"
                logger.error(error_msg)
                deletion_errors.append(error_msg)

            # Delete record from database (hard delete)
            try:
                await self.crud.delete(file, soft_delete=False)
                logger.info(f"Deleted file record from database: {file_id}")
            except Exception as e:
                error_msg = f"Failed to delete file record from database: {str(e)}"
                logger.error(error_msg)
                deletion_errors.append(error_msg)
                raise AppError("Failed to delete file record from database")

            # Check and report results
            if deletion_errors:
                logger.warning(f"File deletion completed with some errors: {'; '.join(deletion_errors)}")
            else:
                logger.info(f"File deleted successfully: {file_id}")

            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            raise AppError(f"Deletion failed: {str(e)}")

    async def rename_file(self, user_id: str, file_id: str, new_name: str) -> Optional[FileCreate]:
        """Rename file (only update database, keep MinIO object unchanged)

        Args:
            user_id: User ID
            file_id: File ID
            new_name: New name
        """
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
        """List all files for user

        Args:
            user_id: User ID
        """
        filter_dict = {"owner_id": user_id}
        files = await self.crud.list(filter_=filter_dict)
        return files


    async def batch_delete_files(self, user_id: str, file_ids: List[str]) -> dict:
        """Delete multiple files at once with comprehensive cleanup

        Args:
            user_id: User ID
            file_ids: List of file IDs to delete
        """
        results = {"successful": [], "failed": []}

        for file_id in file_ids:
            try:
                success = await self.delete_file(user_id, file_id)
                if success:
                    results["successful"].append(file_id)
                else:
                    results["failed"].append({"file_id": file_id, "error": "Deletion failed"})
            except Exception as e:
                logger.error(f"Failed to delete file {file_id}: {str(e)}")
                results["failed"].append({"file_id": file_id, "error": str(e)})

        logger.info(f"Batch deletion completed: {len(results['successful'])} successful, {len(results['failed'])} failed")
        return results

