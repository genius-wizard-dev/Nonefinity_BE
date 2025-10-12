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

    def _generate_unique_filename(self, original_filename: str) -> tuple:
        """Generate unique filename while preserving extension"""
        if not original_filename:
            return str(uuid.uuid4())[:6], ""

        name, ext = os.path.splitext(original_filename)
        # Generate 6-character random string instead of long UUID
        unique_name = str(uuid.uuid4()).replace('-', '')[:6]
        return unique_name, ext

    async def _generate_unique_display_name(self, user_id: str, original_filename: str) -> str:
        """Generate unique display name with number suffix if exists"""
        if not original_filename:
            return str(uuid.uuid4())[:6]

        name, ext = os.path.splitext(original_filename)

        # Check if file with same name exists
        existing_files = await self.crud.list({
            "owner_id": user_id,
            "file_name": name,
            "file_ext": ext
        })

        if not existing_files:
            return name

        # Find the highest number suffix
        max_number = 0
        for file in existing_files:
            if file.file_name == name:
                max_number = max(max_number, 0)
            elif file.file_name.startswith(f"{name}(") and file.file_name.endswith(")"):
                try:
                    # Extract number from filename like "document(1)"
                    number_part = file.file_name[len(name)+1:-1]
                    if number_part.isdigit():
                        max_number = max(max_number, int(number_part))
                except Exception:
                    continue

        # Return name with next number
        return f"{name}({max_number + 1})"


    # async def upload_file(self, user_id: str, file: UploadFile) -> Optional[FileCreate]:
    #     """Upload file to raw/ folder only - simplified version"""
    #     file_create = None

    #     try:
    #         logger.info(f"Starting file upload for user {user_id}, file: {file.filename}")

    #         # Validate file
    #         if not file.filename:
    #             raise AppError("File name is required")

    #         if file.size and file.size > 100 * 1024 * 1024:  # 100MB limit
    #             raise AppError("File size exceeds 100MB limit")

    #         # Get root folder and generate unique filename
    #         root_folder = "raw"
    #         original_name, original_ext = os.path.splitext(file.filename)
    #         unique_filename, file_ext = self._generate_unique_filename(file.filename)

    #         # Create file path: raw/unique_filename.ext
    #         file_path = f"{root_folder}/{unique_filename}{file_ext}"

    #         # Determine content type
    #         content_type = file.content_type
    #         if content_type == "application/octet-stream" and file.filename:
    #             guessed_type, _ = mimetypes.guess_type(file.filename)
    #             if guessed_type:
    #                 content_type = guessed_type

    #         # Create database record first
    #         file_info = FileCreate(
    #             bucket=user_id,
    #             file_name=original_name,
    #             file_ext=file_ext,
    #             file_path=file_path,
    #             file_size=file.size,
    #             file_type=content_type,
    #             owner_id=user_id
    #         )

    #         file_create = await self.crud.create(obj_in=file_info)
    #         logger.info(f"Created database record for file: {file_create.id}")

    #         # Upload file to MinIO
    #         upload_success = self._minio_client.upload_file(
    #             bucket_name=user_id,
    #             file=file,
    #             object_name=file_path
    #         )

    #         if not upload_success:
    #             logger.error(f"MinIO upload failed for file: {file_path}")
    #             raise AppError("Failed to upload file to storage")



    #         logger.info(f"File upload completed successfully: {file_create.id}")
    #         return file_create

    #     except Exception as e:
    #         logger.error(f"File upload failed: {str(e)}")

    #         # Simple rollback operations
    #         rollback_errors = []

    #         # 1. Rollback original file from MinIO
    #         if file_path:
    #             try:
    #                 file_deleted = self._minio_client.delete_file(bucket_name=user_id, file_name=file_path)
    #                 if file_deleted:
    #                     logger.info(f"Rolled back MinIO file: {file_path}")
    #                 else:
    #                     error_msg = f"Failed to delete original file: {file_path}"
    #                     logger.warning(error_msg)
    #                     rollback_errors.append(error_msg)
    #             except Exception as cleanup_error:
    #                 error_msg = f"Failed to cleanup MinIO file: {cleanup_error}"
    #                 logger.error(error_msg)
    #                 rollback_errors.append(error_msg)

    #         # 2. Rollback database record
    #         if file_create:
    #             try:
    #                 await self.crud.delete(file_create, soft_delete=False)  # Hard delete
    #                 logger.info(f"Rolled back database record: {file_create.id}")
    #             except Exception as cleanup_error:
    #                 error_msg = f"Failed to cleanup database record: {cleanup_error}"
    #                 logger.error(error_msg)
    #                 rollback_errors.append(error_msg)

    #         # Log rollback summary
    #         if rollback_errors:
    #             logger.error(f"Rollback completed with errors: {'; '.join(rollback_errors)}")
    #         else:
    #             logger.info("Complete rollback successful")

    #         # Re-raise original exception
    #         if isinstance(e, AppError):
    #             raise e
    #         else:
    #             raise AppError(f"Upload failed: {str(e)}")

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
                await self.crud.delete(file)
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

    async def get_upload_url(self, user_id: str, file_name: str, file_type: str) -> dict:
        """Get presigned upload URL for file

        Args:
            user_id: User ID
            file_name: Original file name
            file_type: File MIME type

        Returns:
            Dict with upload_url, object_name, expires_in
        """
        try:
            # Generate unique object name
            original_name, original_ext = os.path.splitext(file_name)
            unique_filename, file_ext = self._generate_unique_filename(file_name)
            object_name = f"raw/{unique_filename}{file_ext}"

            # Get presigned upload URL
            upload_url = self._minio_client.get_upload_url(
                bucket_name=user_id,
                object_name=object_name,
                expires_minutes=10
            )

            if not upload_url:
                raise AppError("Failed to generate upload URL")

            return {
                "upload_url": upload_url,
                "object_name": object_name,
                "expires_in": 10
            }

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Failed to get upload URL: {str(e)}")
            raise AppError(f"Failed to get upload URL: {str(e)}")

    async def save_file_metadata(self, user_id: str, object_name: str, file_name: str, file_type: str, file_size: int = None) -> FileCreate:
        """Save file metadata to database after upload

        Args:
            user_id: User ID
            object_name: Object name in MinIO
            file_name: Original file name
            file_type: File MIME type
            file_size: File size in bytes

        Returns:
            File object
        """
        try:
            # Generate unique display name (with number suffix if exists)
            unique_display_name = await self._generate_unique_display_name(user_id, file_name)

            # Extract original file name and extension for database
            original_name, original_ext = os.path.splitext(file_name)

            # Create file record with unique display name
            file_info = FileCreate(
                bucket=user_id,
                file_name=unique_display_name,
                file_ext=original_ext,
                file_path=object_name,
                file_size=file_size,
                file_type=file_type,
                owner_id=user_id
            )

            file_create = await self.crud.create(obj_in=file_info)
            return file_create

        except Exception as e:
            logger.error(f"Failed to save file metadata: {str(e)}")
            raise AppError(f"Failed to save file metadata: {str(e)}")

    async def get_download_url(self, user_id: str, file_id: str) -> str:
        """Get presigned download URL for a file

        Args:
            user_id: User ID
            file_id: File ID

        Returns:
            Presigned download URL string
        """
        try:
            # Get file from database
            file = await self.crud.get_by_id(file_id)
            if not file:
                raise AppError("File not found")

            if file.owner_id != user_id:
                raise AppError("Unauthorized: Cannot access file")

            # Generate presigned URL from MinIO with proper filename (single use)
            original_filename = f"{file.file_name}{file.file_ext}"
            download_url = self._minio_client.get_url(
                bucket_name=user_id,
                object_name=file.file_path,
                download_filename=original_filename,

                single_use=True  # URL expires in 1 minute for single use
            )

            if not download_url:
                raise AppError("Failed to generate download URL")

            return download_url

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Failed to get download URL: {str(e)}")
            raise AppError(f"Failed to get download URL: {str(e)}")


    async def get_list_allow_convert(self, user_id: str) -> List[dict]:
        """
        Get list of files that are allowed to be converted to dataset.
        Only returns files, not a single file by id.
        """
        allowed_types = [
            "text/csv",
            "application/csv",
            "text/plain",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/vnd.ms-excel.sheet.macroEnabled.12",
            "application/vnd.ms-excel.template.macroEnabled.12",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.template"
        ]
        files = await self.crud.list(
            filter_={"owner_id": user_id, "file_type": {"$in": allowed_types}}
        )

        return files

    async def get_list_allow_extract(self, user_id: str) -> List[dict]:
        """
        Get list of files that are allowed to be extracted (pdf or txt).
        Only returns files, not a single file by id.
        """
        allowed_types = ["application/pdf", "text/plain"]
        files = await self.crud.list(
            filter_={"owner_id": user_id, "file_type": {"$in": allowed_types}}
        )

        return files
