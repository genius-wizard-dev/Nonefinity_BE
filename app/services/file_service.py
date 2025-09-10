from app.services.minio_client_service import MinIOClientService
from fastapi import UploadFile
from app.schemas.file import FileCreate, FileUpdate
from app.schemas.file_version import FileVersionCreate
from app.crud.file import FileCRUD
from app.crud.file_version import file_version_crud
from app.core.exceptions import AppError
from app.utils import get_logger
from app.utils.file_classifier import FileClassifier
from app.services.duckdb_service import DuckDBService
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
        # Tạo chuỗi 6 ký tự ngẫu nhiên thay vì UUID dài
        unique_name = str(uuid.uuid4()).replace('-', '')[:6]
        return unique_name, ext


    async def upload_file(self, user_id: str, file: UploadFile) -> Optional[FileCreate]:
        """Upload file with comprehensive error handling and rollback"""
        file_create = None
        object_name = None
        parquet_object_name = None
        file_version = None

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

            # Read file content để xử lý theo flow
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer

            # Create database record first
            file_info = FileCreate(
                bucket=user_id,
                file_name=original_name,
                file_ext=file_ext,
                object_name=object_name,
                file_size=file.size,
                file_type=content_type,
                owner_id=user_id,
                version_ids=[] if FileClassifier.is_csv_or_excel(content_type, file_ext) else None
            )

            file_create = await self.crud.create(obj_in=file_info)
            logger.info(f"Created database record for file: {file_create.id}")

            # Upload file gốc to MinIO
            upload_success = self._minio_client.upload_file(
                bucket_name=user_id,
                file=file,
                object_name=object_name
            )

            if not upload_success:
                logger.error(f"MinIO upload failed for file: {object_name}")
                raise AppError("Failed to upload file to storage")

            # Xử lý theo loại file
            if FileClassifier.is_csv_or_excel(content_type, file_ext):
                logger.info(f"Processing CSV/Excel file: {file.filename}")

                # Convert to Parquet
                parquet_object_name = DuckDBService.get_parquet_object_name(object_name, unique_filename, version=1)

                # Phân biệt CSV và Excel
                if file_ext.lower() == ".csv":
                    # CSV: sử dụng DuckDB
                    parquet_success = await DuckDBService.convert_csv_to_parquet_with_duckdb(
                        user_id=user_id,
                        access_key=self.access_key,
                        secret_key=self.secret_key,
                        csv_s3_path=object_name,
                        parquet_s3_path=parquet_object_name
                    )
                else:
                    # Excel: sử dụng pandas (vì DuckDB không đọc trực tiếp Excel)
                    parquet_success = await DuckDBService.convert_excel_to_parquet_with_duckdb(
                        user_id=user_id,
                        excel_s3_path=object_name,
                        parquet_s3_path=parquet_object_name,
                        minio_client=self._minio_client
                    )

                if parquet_success:
                    logger.info(f"Parquet file created successfully with DuckDB: {parquet_object_name}")

                    # Chỉ tạo version cho Parquet (version 1)
                    parquet_version_info = FileVersionCreate(
                        version=1,
                        actions=None,
                        source=parquet_object_name,
                        raw_id=str(file_create.id)
                    )

                    parquet_version = await file_version_crud.create(obj_in=parquet_version_info)

                    # Cập nhật version_ids trong file chính - chỉ có Parquet version
                    update_data = FileUpdate(version_ids=[str(parquet_version.id)])
                    await self.crud.update(file_create, obj_in=update_data)
                    file_version = parquet_version  # Để cleanup trong trường hợp lỗi

                else:
                    logger.warning(f"Failed to convert CSV to Parquet with DuckDB: {parquet_object_name}")
                    # Nếu convert thất bại, tạo version cho file gốc
                    version_info = FileVersionCreate(
                        version=1,
                        actions=None,
                        source=object_name,
                        raw_id=str(file_create.id)
                    )
                    file_version = await file_version_crud.create(obj_in=version_info)
                    update_data = FileUpdate(version_ids=[str(file_version.id)])
                    await self.crud.update(file_create, obj_in=update_data)

            else:
                logger.info(f"Processing non-spreadsheet file: {file.filename}")
                # PDF và các file khác không cần version system, chỉ lưu file gốc
                # Không tạo version record, chỉ giữ file trong MinIO
                file_version = None  # Để cleanup biết không có version record

            # Generate presigned URL and update record
            url = self._minio_client.get_url(bucket_name=user_id, object_name=object_name)
            if url:
                final_update = FileUpdate(url=url)
                await self.crud.update(file_create, obj_in=final_update)

            logger.info(f"File upload completed successfully: {file_create.id}")
            return file_create

        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")

            # Rollback operations
            if file_version:
                try:
                    await file_version_crud.delete(file_version)
                    logger.info(f"Rolled back file version: {file_version.id}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup file version: {cleanup_error}")

            if file_create:
                try:
                    await self.crud.delete(file_create)  # Hard delete
                    logger.info(f"Rolled back database record: {file_create.id}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup database record: {cleanup_error}")

            if parquet_object_name:
                try:
                    self._minio_client.delete_file(bucket_name=user_id, file_name=parquet_object_name)
                    logger.info(f"Rolled back Parquet object: {parquet_object_name}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup Parquet object: {cleanup_error}")

            if object_name:
                try:
                    self._minio_client.delete_file(bucket_name=user_id, file_name=object_name)
                    logger.info(f"Rolled back MinIO object: {object_name}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup MinIO object: {cleanup_error}")

            if isinstance(e, AppError):
                raise e
            else:
                raise AppError(f"Upload failed: {str(e)}")

    async def delete_file(self, user_id: str, file_id: str) -> bool:
        """Delete file permanently from both MongoDB and MinIO"""
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

            # Xóa tất cả versions của file và các file parquet tương ứng
            cleanup_errors = await self._cleanup_file_versions_and_storage(user_id, file_id, file)
            deletion_errors.extend(cleanup_errors)

            # Xóa file gốc từ MinIO
            try:
                main_file_deleted = self._minio_client.delete_file(bucket_name=user_id, file_name=file.object_name)
                if main_file_deleted:
                    logger.info(f"Deleted main file from MinIO: {file.object_name}")
                else:
                    error_msg = f"Failed to delete main file from MinIO: {file.object_name}"
                    logger.error(error_msg)
                    deletion_errors.append(error_msg)
            except Exception as e:
                error_msg = f"Failed to delete main file: {str(e)}"
                logger.error(error_msg)
                deletion_errors.append(error_msg)

            # Xóa record từ database (hard delete)
            try:
                await self.crud.delete(file, soft_delete=False)
                logger.info(f"Deleted file record from database: {file_id}")
            except Exception as e:
                error_msg = f"Failed to delete file record from database: {str(e)}"
                logger.error(error_msg)
                deletion_errors.append(error_msg)
                raise AppError("Failed to delete file record from database")

            # Kiểm tra và báo cáo kết quả
            if deletion_errors:
                logger.warning(f"File deletion completed with some errors: {'; '.join(deletion_errors)}")
                # Vẫn trả về True vì file record đã được xóa, chỉ có một số file storage có thể còn lại
            else:
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

    async def get_file_versions(self, user_id: str, file_id: str) -> List[FileVersionCreate]:
        """Get all versions of a file"""
        try:
            file = await self.crud.get_by_id(file_id)
            if not file or file.owner_id != user_id:
                raise AppError("File not found or unauthorized")

            versions = await file_version_crud.get_versions_by_raw_id(file_id)
            return versions

        except Exception as e:
            logger.error(f"Failed to get file versions: {str(e)}")
            raise AppError(f"Failed to get versions: {str(e)}")


    async def _cleanup_file_versions_and_storage(self, user_id: str, file_id: str, file: FileCreate) -> List[str]:
        """Helper method to clean up all file versions and their storage files"""
        cleanup_errors = []

        try:
            # Lấy tất cả versions
            versions = await file_version_crud.get_versions_by_raw_id(file_id)
            logger.info(f"Found {len(versions)} versions to cleanup for file {file_id}")

            # Xóa từng version
            for version in versions:
                try:
                    # Xóa file version từ MinIO
                    version_deleted = self._minio_client.delete_file(bucket_name=user_id, file_name=version.source)
                    if version_deleted:
                        logger.info(f"Deleted version file from MinIO: {version.source}")
                    else:
                        error_msg = f"Failed to delete version file from MinIO: {version.source}"
                        logger.error(error_msg)
                        cleanup_errors.append(error_msg)

                    # Xóa version record từ database (hard delete)
                    await file_version_crud.delete(version, soft_delete=False)
                    logger.info(f"Deleted version record: {version.id} (version {version.version})")

                except Exception as e:
                    error_msg = f"Failed to delete version {version.id}: {str(e)}"
                    logger.error(error_msg)
                    cleanup_errors.append(error_msg)

            # Xóa toàn bộ thư mục process/ nếu là CSV/Excel file
            if FileClassifier.is_csv_or_excel(file.file_type, file.file_ext):
                try:
                    # Lấy unique filename từ object_name gốc
                    unique_filename = file.object_name.split("/")[-1].split(".")[0]
                    process_folder = f"process/{unique_filename}"

                    # Xóa toàn bộ thư mục process/unique_filename/
                    folder_deleted = self._minio_client.delete_folder(bucket_name=user_id, folder_path=process_folder)
                    if folder_deleted:
                        logger.info(f"Deleted process folder: {process_folder}")
                    else:
                        error_msg = f"Failed to delete process folder: {process_folder}"
                        logger.warning(error_msg)
                        cleanup_errors.append(error_msg)

                except Exception as e:
                    error_msg = f"Failed to delete process folder: {str(e)}"
                    logger.error(error_msg)
                    cleanup_errors.append(error_msg)

        except Exception as e:
            error_msg = f"Failed to cleanup file versions: {str(e)}"
            logger.error(error_msg)
            cleanup_errors.append(error_msg)

        return cleanup_errors

    async def batch_delete_files(self, user_id: str, file_ids: List[str]) -> dict:
        """Delete multiple files at once with comprehensive cleanup"""
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



