from app.services.minio_client_service import MinIOClientService
from app.services.google_services import GoogleServices
from app.schemas.file import FileCreate, FileUpdate
from app.crud import file_crud
from app.core.exceptions import AppError
from app.utils import get_logger
from typing import Optional, List
import uuid
import os

logger = get_logger(__name__)

class FileService:
    def __init__(self, access_key: str, secret_key: str):
        self._minio_client = MinIOClientService(access_key=access_key, secret_key=secret_key)
        self.crud = file_crud
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

    async def delete_file(self, user_id: str, file_id: str) -> bool:
        """Delete file permanently from both MongoDB and MinIO - simplified version

        Args:
            user_id: User ID
            file_id: File ID
        """
        deletion_errors = []

        try:
            logger.info(f"[FILE_DELETE] Starting deletion - user_id: {user_id}, file_id: {file_id}")

            file = await self.crud.get_by_id(file_id)
            if not file:
                logger.warning(f"[FILE_DELETE] File not found - file_id: {file_id}, user_id: {user_id}")
                raise AppError("File not found")

            if file.owner_id != user_id:
                logger.warning(f"[FILE_DELETE] Unauthorized attempt - file_id: {file_id}, file_owner: {file.owner_id}, requester: {user_id}")
                raise AppError("Unauthorized: Cannot delete file")

            logger.info(f"[FILE_DELETE] File found - name: {file.file_name}{file.file_ext}, path: {file.file_path}, size: {file.file_size} bytes")

            # Delete file from MinIO
            try:
                logger.info(f"[FILE_DELETE] Deleting from MinIO - bucket: {user_id}, object: {file.file_path}")
                main_file_deleted = await self._minio_client.async_delete_file(bucket_name=user_id, file_name=file.file_path)
                if main_file_deleted:
                    logger.info(f"[FILE_DELETE] Successfully deleted from MinIO - path: {file.file_path}")
                else:
                    error_msg = f"Failed to delete main file from MinIO: {file.file_path}"
                    logger.error(f"[FILE_DELETE] {error_msg}")
                    deletion_errors.append(error_msg)
            except Exception as e:
                error_msg = f"Failed to delete main file: {str(e)}"
                logger.error(f"[FILE_DELETE] MinIO deletion error - {error_msg}", exc_info=True)
                deletion_errors.append(error_msg)

            # Delete record from database (hard delete)
            try:
                logger.info(f"[FILE_DELETE] Deleting from database - file_id: {file_id}")
                await self.crud.delete(file)
                logger.info(f"[FILE_DELETE] Successfully deleted from database - file_id: {file_id}")
            except Exception as e:
                error_msg = f"Failed to delete file record from database: {str(e)}"
                logger.error(f"[FILE_DELETE] Database deletion error - {error_msg}", exc_info=True)
                deletion_errors.append(error_msg)
                raise AppError("Failed to delete file record from database")

            # Check and report results
            if deletion_errors:
                logger.warning(f"[FILE_DELETE] Completed with errors - file_id: {file_id}, errors: {'; '.join(deletion_errors)}")
            else:
                logger.info(f"[FILE_DELETE] Successfully completed - file_id: {file_id}, name: {file.file_name}{file.file_ext}")

            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"[FILE_DELETE] Deletion failed - user_id: {user_id}, file_id: {file_id}, error: {str(e)}", exc_info=True)
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
            upload_url = await self._minio_client.async_get_upload_url(
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

    async def save_file_metadata(self, user_id: str, object_name: str, file_name: str, file_type: str, file_size: int = None, source_file: str = "upload") -> FileCreate:
        """Save file metadata to database after upload

        Args:
            user_id: User ID
            object_name: Object name in MinIO
            file_name: Original file name
            file_type: File MIME type
            file_size: File size in bytes
            source_file: File source ('upload' or 'drive')

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
                owner_id=user_id,
                source_file=source_file
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
            download_url = await self._minio_client.async_get_url(
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

        logger.info(f"Files: {files}")

        return files

    async def import_from_drive(self, user_id: str, file_id: str, file_name: str, file_type: str, access_token: str) -> FileCreate:
        """
        Import file from Google Drive to MinIO storage

        Args:
            user_id: User ID
            file_id: Google Drive file ID
            file_name: Original file name
            file_type: File type ('sheet' or 'pdf')
            access_token: Google OAuth access token

        Returns:
            FileCreate object with imported file metadata
        """
        try:
            logger.info(f"[DRIVE_IMPORT] Starting import - user_id: {user_id}, file_id: {file_id}, file_type: {file_type}, file_name: {file_name}")

            # Get file info from Google Drive
            file_info = await GoogleServices.async_get_file_info(access_token, file_id)
            drive_file_name = file_info.get("name", file_name)
            drive_mime_type = file_info.get("mimeType", "")
            logger.info(f"[DRIVE_IMPORT] File info retrieved - name: {drive_file_name}, mime_type: {drive_mime_type}")

            # Determine file extension and MIME type based on file_type
            if file_type == "sheet":
                # Check if it's a native Google Sheet or uploaded Excel file
                is_google_sheet = drive_mime_type == "application/vnd.google-apps.spreadsheet"
                is_excel_file = drive_mime_type in [
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "application/vnd.ms-excel",
                    "application/vnd.ms-excel.sheet.macroEnabled.12"
                ]

                if is_google_sheet:
                    # Export Google Sheet to Excel format
                    try:
                        file_content = await GoogleServices.async_export_sheet(access_token, file_id, format='xlsx')
                        file_ext = ".xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        # Use original name from Drive, add .xlsx if not present
                        if not drive_file_name.endswith('.xlsx') and not drive_file_name.endswith('.xls'):
                            drive_file_name = f"{drive_file_name}.xlsx"
                    except Exception as e:
                        logger.error(f"Failed to export Google Sheet, trying direct download: {str(e)}")
                        # Fallback: try to download directly if export fails
                        file_content = await GoogleServices.async_download_file(access_token, file_id, drive_mime_type)
                        # Determine extension from original file
                        if drive_file_name.endswith('.xlsx'):
                            file_ext = ".xlsx"
                            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        elif drive_file_name.endswith('.xls'):
                            file_ext = ".xls"
                            mime_type = "application/vnd.ms-excel"
                        else:
                            file_ext = ".xlsx"
                            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            drive_file_name = f"{drive_file_name}.xlsx"
                elif is_excel_file:
                    # Download Excel file directly (already in Excel format)
                    file_content = await GoogleServices.async_download_file(access_token, file_id, drive_mime_type)
                    # Determine extension from original file
                    if drive_file_name.endswith('.xlsx'):
                        file_ext = ".xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    elif drive_file_name.endswith('.xls'):
                        file_ext = ".xls"
                        mime_type = "application/vnd.ms-excel"
                    else:
                        # Default to xlsx if extension not found
                        file_ext = ".xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        drive_file_name = f"{drive_file_name}.xlsx"
                else:
                    # Unknown sheet type, try to export first, then download
                    try:
                        file_content = await GoogleServices.async_export_sheet(access_token, file_id, format='xlsx')
                        file_ext = ".xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        if not drive_file_name.endswith('.xlsx') and not drive_file_name.endswith('.xls'):
                            drive_file_name = f"{drive_file_name}.xlsx"
                    except Exception:
                        # Fallback to direct download
                        file_content = await GoogleServices.async_download_file(access_token, file_id, drive_mime_type)
                        file_ext = ".xlsx"
                        mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        if not drive_file_name.endswith('.xlsx') and not drive_file_name.endswith('.xls'):
                            drive_file_name = f"{drive_file_name}.xlsx"
            elif file_type == "pdf":
                # Download PDF directly
                file_content = GoogleServices.download_file(access_token, file_id, drive_mime_type)
                file_ext = ".pdf"
                mime_type = "application/pdf"
                # Use original name from Drive, add .pdf if not present
                if not drive_file_name.endswith('.pdf'):
                    drive_file_name = f"{drive_file_name}.pdf"
            else:
                raise AppError(f"Unsupported file type: {file_type}")

            # Generate unique filename for storage
            unique_filename, _ = self._generate_unique_filename(drive_file_name)
            object_name = f"raw/{unique_filename}{file_ext}"

            # Upload to MinIO
            file_size = len(file_content)
            upload_success = await self._minio_client.async_upload_bytes(
                bucket_name=user_id,
                object_name=object_name,
                data=file_content,
                content_type=mime_type
            )

            if not upload_success:
                raise AppError("Failed to upload file to MinIO")

            logger.info(f"[DRIVE_IMPORT] File uploaded to MinIO - bucket: {user_id}, object: {object_name}, size: {file_size} bytes")

            # Save metadata to database
            file_metadata = await self.save_file_metadata(
                user_id=user_id,
                object_name=object_name,
                file_name=drive_file_name,
                file_type=mime_type,
                file_size=file_size,
                source_file="drive"
            )

            logger.info(f"[DRIVE_IMPORT] Successfully imported file - file_id: {file_metadata.id}, name: {drive_file_name}, type: {mime_type}, size: {file_size} bytes")
            return file_metadata

        except AppError:
            raise
        except Exception as e:
            logger.error(f"[DRIVE_IMPORT] Failed to import file - user_id: {user_id}, file_id: {file_id}, error: {str(e)}", exc_info=True)
            raise AppError(f"Failed to import file from Drive: {str(e)}")
