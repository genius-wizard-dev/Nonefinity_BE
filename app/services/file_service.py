from app.services.minio_service import MinIOService
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
        self._minio_service = MinIOService(access_key=access_key, secret_key=secret_key)
        self.crud = crud or FileCRUD()

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        if not original_filename:
            return str(uuid.uuid4())

        _, ext = os.path.splitext(original_filename)
        unique_name = f"{uuid.uuid4()}{ext}"
        return unique_name

    async def upload_file(self, user_id: str, file: UploadFile, folder_path: str = "/") -> Optional[FileCreate]:
        """Upload file with comprehensive error handling and rollback"""
        file_create = None
        full_object_path = None

        try:
            logger.info(f"Starting file upload for user {user_id}, file: {file.filename}")

            # Validate file
            if not file.filename:
                raise AppError("File name is required")

            if file.size and file.size > 100 * 1024 * 1024:  # 100MB limit
                raise AppError("File size exceeds 100MB limit")

            # Validate folder path format
            if not folder_path.startswith('/'):
                folder_path = '/' + folder_path

            unique_object_name = self._generate_unique_filename(file.filename)

            # Create full object path: folder_path + unique_filename
            if folder_path == "/":
                full_object_path = unique_object_name
            else:
                # Remove leading slash from folder_path and ensure proper path
                clean_folder_path = folder_path.lstrip('/')
                if not clean_folder_path.endswith('/'):
                    clean_folder_path += '/'
                full_object_path = clean_folder_path + unique_object_name

            # Determine content type
            content_type = file.content_type
            if content_type == "application/octet-stream" and file.filename:
                guessed_type, _ = mimetypes.guess_type(file.filename)
                if guessed_type:
                    content_type = guessed_type

            # Check if file with same name exists in folder
            existing_file = await self.crud.get_by_object_name(user_id, full_object_path)
            if existing_file:
                raise AppError(f"File already exists in folder: {file.filename}")

            # Create database record first
            file_info = FileCreate(
                bucket=user_id,
                file_name=file.filename,
                object_name=full_object_path,
                file_size=file.size,
                file_type=content_type,
                owner_id=user_id,
                folder_path=folder_path
            )

            file_create = await self.crud.create(obj_in=file_info)
            logger.info(f"Created database record for file: {file_create.id}")

            # Upload to MinIO
            upload_success = self._minio_service.upload_file(
                user_id=user_id,
                file=file,
                object_name=full_object_path
            )

            if not upload_success:
                logger.error(f"MinIO upload failed for file: {full_object_path}")
                raise AppError("Failed to upload file to storage")

            # Generate presigned URL and update record
            url = self._minio_service.get_url(bucket_name=user_id, object_name=full_object_path)
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
                    await self.crud.delete(file_create, soft_delete=False)
                    logger.info(f"Rolled back database record: {file_create.id}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup database record: {cleanup_error}")

            if full_object_path:
                try:
                    self._minio_service.delete_file(user_id=user_id, file_name=full_object_path)
                    logger.info(f"Rolled back MinIO object: {full_object_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup MinIO object: {cleanup_error}")

            if isinstance(e, AppError):
                raise e
            else:
                raise AppError(f"Upload failed: {str(e)}")

    async def delete_file(self, user_id: str, file_id: str) -> bool:
        """Delete file with proper validation and error handling"""
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
            minio_deleted = self._minio_service.delete_file(user_id=user_id, file_name=file.object_name)
            if not minio_deleted:
                logger.error(f"Failed to delete file from MinIO: {file.object_name}")
                raise AppError("Failed to delete file from storage")

            # Delete from database (soft delete)
            await self.crud.delete(file, soft_delete=True)

            logger.info(f"File deleted successfully: {file_id}")
            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            raise AppError(f"Deletion failed: {str(e)}")

    async def list_files(self, user_id: str, folder_path: str = None) -> List[FileCreate]:
        filter_dict = {"owner_id": user_id}
        if folder_path is not None:
            filter_dict["folder_path"] = folder_path
        files = await self.crud.list(filter_=filter_dict, include_deleted=False)
        return files

    async def list_files_in_folder(self, user_id: str, folder_path: str = "/") -> List[dict]:
        """
        List files in a specific folder from both database and MinIO
        """
        # Get files from MinIO
        minio_files = self._minio_service.list_files_in_folder(user_id, folder_path)

        # Get files from database for additional metadata
        db_files = await self.list_files(user_id, folder_path)

        # Combine MinIO and database data
        result = []
        for minio_file in minio_files:
            # Find matching database record
            db_file = next((f for f in db_files if f.object_name == minio_file['object_name']), None)

            file_info = {
                'object_name': minio_file['object_name'],
                'file_name': db_file.file_name if db_file else minio_file['object_name'].split('/')[-1],
                'size': minio_file['size'],
                'last_modified': minio_file['last_modified'],
                'file_type': db_file.file_type if db_file else 'unknown',
                'url': self._minio_service.get_url(user_id, minio_file['object_name']) if db_file else None,
                'id': str(db_file.id) if db_file else None
            }
            result.append(file_info)

        return result

    async def move_file_to_folder(self, user_id: str, file_id: str, new_folder_path: str) -> bool:
        """Move file to a different folder with validation"""
        try:
            logger.info(f"Moving file {file_id} to folder {new_folder_path} for user {user_id}")

            file = await self.crud.get_by_id(file_id)
            if not file or file.owner_id != user_id:
                raise AppError("File not found or unauthorized")

            # Validate new folder path
            if not new_folder_path.startswith('/'):
                new_folder_path = '/' + new_folder_path

            # Calculate new object name
            filename_with_ext = file.object_name.split('/')[-1]
            if new_folder_path == "/":
                new_object_name = filename_with_ext
            else:
                clean_folder_path = new_folder_path.lstrip('/')
                if not clean_folder_path.endswith('/'):
                    clean_folder_path += '/'
                new_object_name = clean_folder_path + filename_with_ext

            # Check if file already exists in destination
            existing = await self.crud.get_by_object_name(user_id, new_object_name)
            if existing:
                raise AppError("File with same name already exists in destination folder")

            # Move in MinIO by copying and deleting
            old_object_name = file.object_name
            copy_source = {"Bucket": user_id, "Key": old_object_name}

            try:
                self._minio_service.client.copy_object(user_id, new_object_name, copy_source)
                self._minio_service.client.remove_object(user_id, old_object_name)
            except Exception as e:
                logger.error(f"Failed to move file in MinIO: {e}")
                raise AppError("Failed to move file in storage")

            # Update database record
            update_data = FileUpdate(
                folder_path=new_folder_path,
                object_name=new_object_name
            )
            await self.crud.update(file, obj_in=update_data)

            logger.info(f"File moved successfully: {file_id}")
            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"File move failed: {str(e)}")
            raise AppError(f"Move failed: {str(e)}")

    async def copy_file(self, user_id: str, file_id: str, new_folder_path: str, new_name: str = None) -> Optional[FileCreate]:
        """Copy file to a new location"""
        try:
            logger.info(f"Copying file {file_id} for user {user_id}")

            original_file = await self.crud.get_by_id(file_id)
            if not original_file or original_file.owner_id != user_id:
                raise AppError("File not found or unauthorized")

            # Prepare new file name
            if not new_name:
                new_name = f"Copy of {original_file.file_name}"

            # Generate new object name
            file_ext = os.path.splitext(original_file.file_name)[1]
            unique_object_name = f"{uuid.uuid4()}{file_ext}"

            if new_folder_path == "/":
                new_object_name = unique_object_name
            else:
                clean_folder_path = new_folder_path.lstrip('/')
                if not clean_folder_path.endswith('/'):
                    clean_folder_path += '/'
                new_object_name = clean_folder_path + unique_object_name

            # Copy in MinIO
            copy_source = {"Bucket": user_id, "Key": original_file.object_name}
            try:
                self._minio_service.client.copy_object(user_id, new_object_name, copy_source)
            except Exception as e:
                logger.error(f"Failed to copy file in MinIO: {e}")
                raise AppError("Failed to copy file in storage")

            # Create new database record
            new_file_data = FileCreate(
                owner_id=user_id,
                bucket=user_id,
                object_name=new_object_name,
                file_name=new_name,
                file_type=original_file.file_type,
                file_size=original_file.file_size,
                folder_path=new_folder_path
            )

            new_file = await self.crud.create(obj_in=new_file_data)

            # Generate URL for new file
            url = self._minio_service.get_url(bucket_name=user_id, object_name=new_object_name)
            if url:
                update_data = FileUpdate(url=url)
                await self.crud.update(new_file, obj_in=update_data)

            logger.info(f"File copied successfully: {file_id} -> {new_file.id}")
            return new_file

        except AppError:
            raise
        except Exception as e:
            logger.error(f"File copy failed: {str(e)}")
            raise AppError(f"Copy failed: {str(e)}")
