import asyncio
from minio import Minio
from app.configs.settings import settings
from app.utils import get_logger
from io import BytesIO
from datetime import timedelta

logger = get_logger(__name__)


class MinIOClientService:
    def __init__(self, access_key: str, secret_key: str):
        """
        Create a new MinIO client for each instance.
        No more client pooling to avoid RAM issues.
        """
        self.access_key = access_key
        self.secret_key = secret_key

        # Always create a new client
        self.client = Minio(
            endpoint=settings.MINIO_URL.replace(
                "http://", "").replace("https://", ""),
            access_key=access_key,
            secret_key=secret_key,
            secure=settings.MINIO_SSL
        )

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists (synchronous, deprecated - use async_bucket_exists)"""
        return self.client.bucket_exists(bucket_name)

    async def async_bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists (async)"""
        return await asyncio.to_thread(self.client.bucket_exists, bucket_name)

    def make_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket (synchronous, deprecated - use async_make_bucket)"""
        try:
            self.client.make_bucket(bucket_name)
            return True
        except Exception as e:
            logger.error(f"Error creating bucket {bucket_name}: {e}")
            return False

    async def async_make_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket (async)"""
        try:
            await asyncio.to_thread(self.client.make_bucket, bucket_name)
            return True
        except Exception as e:
            logger.error(f"Error creating bucket {bucket_name}: {e}")
            return False

    def remove_bucket(self, bucket_name: str) -> bool:
        """Remove a bucket (synchronous, deprecated - use async_remove_bucket)"""
        try:
            self.client.remove_bucket(bucket_name)
            return True
        except Exception as e:
            logger.error(f"Error removing bucket {bucket_name}: {e}")
            return False

    async def async_remove_bucket(self, bucket_name: str) -> bool:
        """Remove a bucket (async)"""
        try:
            await asyncio.to_thread(self.client.remove_bucket, bucket_name)
            return True
        except Exception as e:
            logger.error(f"Error removing bucket {bucket_name}: {e}")
            return False

    def list_objects(self, bucket_name: str, prefix: str = None, recursive: bool = False):
        """List objects in bucket (synchronous, deprecated - use async_list_objects)"""
        return self.client.list_objects(bucket_name, prefix=prefix, recursive=recursive)

    async def async_list_objects(self, bucket_name: str, prefix: str = None, recursive: bool = False):
        """List objects in bucket (async)"""
        return await asyncio.to_thread(self.client.list_objects, bucket_name, prefix=prefix, recursive=recursive)

    def remove_object(self, bucket_name: str, object_name: str) -> bool:
        """Remove an object from bucket (synchronous, deprecated - use async_remove_object)"""
        try:
            self.client.remove_object(bucket_name, object_name)
            return True
        except Exception as e:
            logger.error(
                f"Error removing object {object_name} from {bucket_name}: {e}")
            return False

    async def async_remove_object(self, bucket_name: str, object_name: str) -> bool:
        """Remove an object from bucket (async)"""
        try:
            await asyncio.to_thread(self.client.remove_object, bucket_name, object_name)
            return True
        except Exception as e:
            logger.error(
                f"Error removing object {object_name} from {bucket_name}: {e}")
            return False

    def get_upload_url(self, bucket_name: str, object_name: str, expires_minutes: int = 10) -> str:
        """Get presigned URL for uploading an object (synchronous, deprecated - use async_get_upload_url)

        Args:
            bucket_name: Bucket name
            object_name: Object name
            expires_minutes: URL expiry time in minutes
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            url = self.client.presigned_put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(minutes=expires_minutes)
            )
            return url

        except Exception as e:
            logger.error(
                f"Error getting upload URL for {bucket_name}/{object_name}: {e}")
            return ""

    async def async_get_upload_url(self, bucket_name: str, object_name: str, expires_minutes: int = 10) -> str:
        """Get presigned URL for uploading an object (async)

        Args:
            bucket_name: Bucket name
            object_name: Object name
            expires_minutes: URL expiry time in minutes
        """
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            def _get_url():
                return self.client.presigned_put_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    expires=timedelta(minutes=expires_minutes)
                )

            url = await asyncio.to_thread(_get_url)
            return url

        except Exception as e:
            logger.error(
                f"Error getting upload URL for {bucket_name}/{object_name}: {e}")
            return ""

    def get_url(self, bucket_name: str, object_name: str, download_filename: str = None, single_use: bool = True) -> str:
        """Get presigned URL to access an object with custom filename (synchronous, deprecated - use async_get_url)

        Args:
            bucket_name: Bucket name
            object_name: Object name
            download_filename: Custom filename for download
            single_use: If True, URL expires in 1 minute for single use
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            # Set up response headers for proper filename
            response_headers = {}
            if download_filename:
                response_headers[
                    "response-content-disposition"] = f'attachment; filename="{download_filename}"'

            # Set expiry time based on single_use flag
            if single_use:
                expires_time = timedelta(minutes=1)  # 1 minute for single use
            else:
                # 10 minutes for normal use
                expires_time = timedelta(minutes=10)

            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires_time,
                response_headers=response_headers
            )
            return url

        except Exception as e:
            logger.error(
                f"Error getting URL for {bucket_name}/{object_name}: {e}")
            return ""

    async def async_get_url(self, bucket_name: str, object_name: str, download_filename: str = None, single_use: bool = True) -> str:
        """Get presigned URL to access an object with custom filename (async)

        Args:
            bucket_name: Bucket name
            object_name: Object name
            download_filename: Custom filename for download
            single_use: If True, URL expires in 1 minute for single use
        """
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            # Set up response headers for proper filename
            response_headers = {}
            if download_filename:
                response_headers[
                    "response-content-disposition"] = f'attachment; filename="{download_filename}"'

            # Set expiry time based on single_use flag
            if single_use:
                expires_time = timedelta(minutes=1)  # 1 minute for single use
            else:
                # 10 minutes for normal use
                expires_time = timedelta(minutes=10)

            def _get_url():
                return self.client.presigned_get_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    expires=expires_time,
                    response_headers=response_headers
                )

            url = await asyncio.to_thread(_get_url)
            return url

        except Exception as e:
            logger.error(
                f"Error getting URL for {bucket_name}/{object_name}: {e}")
            return ""

    # def upload_file(self, bucket_name: str, file: UploadFile, object_name: str) -> bool:
    #     """Upload a file to bucket"""
    #     try:
    #         if not self.client.bucket_exists(bucket_name):
    #             raise ValueError(f"Bucket {bucket_name} does not exist")

    #         self.client.put_object(
    #             bucket_name=bucket_name,
    #             object_name=object_name,
    #             data=file.file,
    #             length=file.size
    #         )
    #         return True

    #     except Exception as e:
    #         logger.error(f"Error uploading file to {bucket_name}: {e}")
    #         return False

    def upload_bytes(self, bucket_name: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload bytes data to bucket (synchronous, deprecated - use async_upload_bytes)"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            data_stream = BytesIO(data)
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data_stream,
                length=len(data),
                content_type=content_type
            )
            return True

        except Exception as e:
            logger.error(
                f"Error uploading bytes to {bucket_name}/{object_name}: {e}")
            return False

    async def async_upload_bytes(self, bucket_name: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload bytes data to bucket (async)"""
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            def _upload():
                data_stream = BytesIO(data)
                self.client.put_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    data=data_stream,
                    length=len(data),
                    content_type=content_type
                )
                return True

            return await asyncio.to_thread(_upload)

        except Exception as e:
            logger.error(
                f"Error uploading bytes to {bucket_name}/{object_name}: {e}")
            return False

    def get_object_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Download an object and return raw bytes (synchronous, deprecated - use async_get_object_bytes)"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            response = self.client.get_object(bucket_name, object_name)
            try:
                data = response.read()
                return data
            finally:
                response.close()
                response.release_conn()
        except Exception as e:
            logger.error(
                f"Error downloading object {bucket_name}/{object_name}: {e}")
            return b""

    async def async_get_object_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Download an object and return raw bytes (async)"""
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            def _download():
                response = self.client.get_object(bucket_name, object_name)
                try:
                    data = response.read()
                    return data
                finally:
                    response.close()
                    response.release_conn()

            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.error(
                f"Error downloading object {bucket_name}/{object_name}: {e}")
            return b""

    def delete_file(self, bucket_name: str, file_name: str) -> bool:
        """Delete a file from bucket (synchronous, deprecated - use async_delete_file)"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            self.client.remove_object(
                bucket_name=bucket_name, object_name=file_name)
            return True

        except Exception as e:
            logger.error(
                f"Error deleting file {file_name} from {bucket_name}: {e}")
            return False

    async def async_delete_file(self, bucket_name: str, file_name: str) -> bool:
        """Delete a file from bucket (async)"""
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            await asyncio.to_thread(self.client.remove_object, bucket_name, file_name)
            return True

        except Exception as e:
            logger.error(
                f"Error deleting file {file_name} from {bucket_name}: {e}")
            return False

    def create_folder(self, bucket_name: str, folder_path: str) -> bool:
        """Create a folder in MinIO by creating an empty object with folder path (synchronous, deprecated - use async_create_folder)"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            # MinIO creates folders by having objects with path prefixes
            # We create an empty placeholder object to represent the folder
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'

            # Create empty object to represent folder
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=folder_path + '.keep',  # placeholder file
                data=BytesIO(b''),
                length=0
            )
            return True

        except Exception as e:
            logger.error(
                f"Error creating folder {folder_path} in {bucket_name}: {e}")
            return False

    async def async_create_folder(self, bucket_name: str, folder_path: str) -> bool:
        """Create a folder in MinIO by creating an empty object with folder path (async)"""
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            # MinIO creates folders by having objects with path prefixes
            # We create an empty placeholder object to represent the folder
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'

            def _create():
                self.client.put_object(
                    bucket_name=bucket_name,
                    object_name=folder_path + '.keep',  # placeholder file
                    data=BytesIO(b''),
                    length=0
                )
                return True

            return await asyncio.to_thread(_create)

        except Exception as e:
            logger.error(
                f"Error creating folder {folder_path} in {bucket_name}: {e}")
            return False

    def delete_folder(self, bucket_name: str, folder_path: str) -> bool:
        """Delete a folder and all its contents from MinIO (synchronous, deprecated - use async_delete_folder)"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'

            # List all objects in the folder
            objects = self.client.list_objects(
                bucket_name, prefix=folder_path, recursive=True)

            # Delete all objects in the folder
            for obj in objects:
                self.client.remove_object(bucket_name, obj.object_name)

            return True

        except Exception as e:
            logger.error(
                f"Error deleting folder {folder_path} from {bucket_name}: {e}")
            return False

    async def async_delete_folder(self, bucket_name: str, folder_path: str) -> bool:
        """Delete a folder and all its contents from MinIO (async)"""
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'

            def _delete():
                # List all objects in the folder
                objects = self.client.list_objects(
                    bucket_name, prefix=folder_path, recursive=True)

                # Delete all objects in the folder
                for obj in objects:
                    self.client.remove_object(bucket_name, obj.object_name)

                return True

            return await asyncio.to_thread(_delete)

        except Exception as e:
            logger.error(
                f"Error deleting folder {folder_path} from {bucket_name}: {e}")
            return False

    def rename_folder(self, bucket_name: str, old_path: str, new_path: str) -> bool:
        """Rename/move a folder by copying all objects to new path and deleting old ones (synchronous, deprecated - use async_rename_folder)"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            if old_path and not old_path.endswith('/'):
                old_path += '/'
            if new_path and not new_path.endswith('/'):
                new_path += '/'

            # List all objects in the old folder
            objects = list(self.client.list_objects(
                bucket_name, prefix=old_path, recursive=True))

            # Copy each object to new location
            for obj in objects:
                old_object_name = obj.object_name
                new_object_name = old_object_name.replace(
                    old_path, new_path, 1)

                # Copy object
                copy_source = {"Bucket": bucket_name, "Key": old_object_name}
                self.client.copy_object(
                    bucket_name, new_object_name, copy_source)

                # Delete old object
                self.client.remove_object(bucket_name, old_object_name)

            return True

        except Exception as e:
            logger.error(
                f"Error renaming folder from {old_path} to {new_path} in {bucket_name}: {e}")
            return False

    async def async_rename_folder(self, bucket_name: str, old_path: str, new_path: str) -> bool:
        """Rename/move a folder by copying all objects to new path and deleting old ones (async)"""
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            if old_path and not old_path.endswith('/'):
                old_path += '/'
            if new_path and not new_path.endswith('/'):
                new_path += '/'

            def _rename():
                # List all objects in the old folder
                objects = list(self.client.list_objects(
                    bucket_name, prefix=old_path, recursive=True))

                # Copy each object to new location
                for obj in objects:
                    old_object_name = obj.object_name
                    new_object_name = old_object_name.replace(
                        old_path, new_path, 1)

                    # Copy object
                    copy_source = {"Bucket": bucket_name, "Key": old_object_name}
                    self.client.copy_object(
                        bucket_name, new_object_name, copy_source)

                    # Delete old object
                    self.client.remove_object(bucket_name, old_object_name)

                return True

            return await asyncio.to_thread(_rename)

        except Exception as e:
            logger.error(
                f"Error renaming folder from {old_path} to {new_path} in {bucket_name}: {e}")
            return False

    def move_folder(self, bucket_name: str, old_path: str, new_path: str) -> bool:
        """Move a folder (same as rename) (synchronous, deprecated - use async_move_folder)"""
        return self.rename_folder(bucket_name, old_path, new_path)

    async def async_move_folder(self, bucket_name: str, old_path: str, new_path: str) -> bool:
        """Move a folder (same as rename) (async)"""
        return await self.async_rename_folder(bucket_name, old_path, new_path)

    def list_files_in_folder(self, bucket_name: str, folder_path: str = "") -> list:
        """List all files in a specific folder (synchronous, deprecated - use async_list_files_in_folder)"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            # Ensure folder_path format
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'
            elif folder_path == "/original":
                folder_path = ""

            # List objects with folder prefix, but not recursive to get only direct children
            objects = self.client.list_objects(
                bucket_name, prefix=folder_path, recursive=False)

            files = []
            for obj in objects:
                # Skip folder placeholders and only return actual files
                if not obj.object_name.endswith('/') and not obj.object_name.endswith('.keep'):
                    files.append({
                        'object_name': obj.object_name,
                        'size': obj.size,
                        'last_modified': obj.last_modified,
                        'etag': obj.etag
                    })

            return files

        except Exception as e:
            logger.error(
                f"Error listing files in folder {folder_path} from {bucket_name}: {e}")
            return []

    async def async_list_files_in_folder(self, bucket_name: str, folder_path: str = "") -> list:
        """List all files in a specific folder (async)"""
        try:
            if not await self.async_bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            # Ensure folder_path format
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'
            elif folder_path == "/original":
                folder_path = ""

            def _list():
                # List objects with folder prefix, but not recursive to get only direct children
                objects = self.client.list_objects(
                    bucket_name, prefix=folder_path, recursive=False)

                files = []
                for obj in objects:
                    # Skip folder placeholders and only return actual files
                    if not obj.object_name.endswith('/') and not obj.object_name.endswith('.keep'):
                        files.append({
                            'object_name': obj.object_name,
                            'size': obj.size,
                            'last_modified': obj.last_modified,
                            'etag': obj.etag
                        })

                return files

            return await asyncio.to_thread(_list)

        except Exception as e:
            logger.error(
                f"Error listing files in folder {folder_path} from {bucket_name}: {e}")
            return []
