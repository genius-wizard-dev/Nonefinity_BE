import os
from typing import Optional, List
from minio import Minio
from minio.error import S3Error
from app.configs.settings import settings
from app.utils import get_logger
import io

logger = get_logger(__name__)

class MinioClient:
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool = False,
    ):
        """
        Initialize MinIO client

        Args:
            endpoint: MinIO server endpoint
            access_key: Access key for authentication
            secret_key: Secret key for authentication
            secure: Whether to use HTTPS
            bucket_name: Default bucket name
        """
        self.client = Minio(
            endpoint=settings.MINIO_URL,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")

    def create_folder(self, folder_path: str) -> bool:
        """
        Create a folder (empty object with trailing slash)

        Args:
            folder_path: Path of the folder to create (will add trailing slash if missing)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not folder_path.endswith('/'):
                folder_path += '/'

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=folder_path,
                data=io.BytesIO(b""),
                length=0
            )
            logger.info(f"Created folder '{folder_path}'")
            return True
        except S3Error as e:
            logger.error(f"Error creating folder '{folder_path}': {e}")
            return False

    def upload_file(self, local_file_path: str, object_name: str) -> bool:
        """
        Upload a file to MinIO

        Args:
            local_file_path: Path to local file
            object_name: Object name in MinIO (can include folder path)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=local_file_path
            )
            logger.info(f"Uploaded '{local_file_path}' to '{object_name}'")
            return True
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            return False

    def upload_data(self, data: bytes, object_name: str) -> bool:
        """
        Upload data directly to MinIO

        Args:
            data: Bytes data to upload
            object_name: Object name in MinIO

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=io.BytesIO(data),
                length=len(data)
            )
            logger.info(f"Uploaded data to '{object_name}'")
            return True
        except S3Error as e:
            logger.error(f"Error uploading data: {e}")
            return False

    def download_file(self, object_name: str, local_file_path: str) -> bool:
        """
        Download a file from MinIO

        Args:
            object_name: Object name in MinIO
            local_file_path: Local path to save the file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=local_file_path
            )
            logger.info(f"Downloaded '{object_name}' to '{local_file_path}'")
            return True
        except S3Error as e:
            logger.error(f"Error downloading file: {e}")
            return False

    def get_object_data(self, object_name: str) -> Optional[bytes]:
        """
        Get object data as bytes

        Args:
            object_name: Object name in MinIO

        Returns:
            bytes: Object data if successful, None otherwise
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"Retrieved data from '{object_name}'")
            return data
        except S3Error as e:
            logger.error(f"Error getting object data: {e}")
            return None

    def delete_object(self, object_name: str) -> bool:
        """
        Delete an object from MinIO

        Args:
            object_name: Object name to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            logger.info(f"Deleted '{object_name}'")
            return True
        except S3Error as e:
            logger.error(f"Error deleting object: {e}")
            return False

    def delete_folder(self, folder_path: str) -> bool:
        """
        Delete a folder and all its contents

        Args:
            folder_path: Folder path to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not folder_path.endswith('/'):
                folder_path += '/'

            # List all objects in the folder
            objects = self.list_objects(folder_path)

            # Delete all objects
            for obj in objects:
                self.delete_object(obj)

            # Delete the folder itself
            self.delete_object(folder_path)

            logger.info(f"Deleted folder '{folder_path}' and all its contents")
            return True
        except Exception as e:
            logger.error(f"Error deleting folder: {e}")
            return False

    def rename_object(self, old_name: str, new_name: str) -> bool:
        """
        Rename an object (copy and delete)

        Args:
            old_name: Current object name
            new_name: New object name

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Copy object to new name
            self.client.copy_object(
                bucket_name=self.bucket_name,
                object_name=new_name,
                source=f"{self.bucket_name}/{old_name}"
            )

            # Delete old object
            self.delete_object(old_name)

            logger.info(f"Renamed '{old_name}' to '{new_name}'")
            return True
        except S3Error as e:
            logger.error(f"Error renaming object: {e}")
            return False

    def list_objects(self, prefix: str = "", recursive: bool = True) -> List[str]:
        """
        List objects in bucket with optional prefix

        Args:
            prefix: Prefix to filter objects
            recursive: Whether to list recursively

        Returns:
            List[str]: List of object names
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            object_names = [obj.object_name for obj in objects]
            logger.info(f"Listed {len(object_names)} objects with prefix '{prefix}'")
            return object_names
        except S3Error as e:
            logger.error(f"Error listing objects: {e}")
            return []

    def object_exists(self, object_name: str) -> bool:
        """
        Check if an object exists

        Args:
            object_name: Object name to check

        Returns:
            bool: True if exists, False otherwise
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return True
        except S3Error:
            return False

    def get_object_info(self, object_name: str) -> Optional[dict]:
        """
        Get object information

        Args:
            object_name: Object name

        Returns:
            dict: Object information if successful, None otherwise
        """
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return {
                'object_name': stat.object_name,
                'size': stat.size,
                'etag': stat.etag,
                'last_modified': stat.last_modified,
                'content_type': stat.content_type,
                'metadata': stat.metadata
            }
        except S3Error as e:
            logger.error(f"Error getting object info: {e}")
            return None

