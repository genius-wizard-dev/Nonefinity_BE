from minio import Minio
from app.configs.settings import settings
from app.utils import get_logger
from fastapi import UploadFile
from io import BytesIO

logger = get_logger(__name__)


class MinIOClientService:
    def __init__(self, access_key: str, secret_key: str):
        """
        Create a new MinIO client for each instance.
        No more client pooling to avoid RAM issues.
        """
        self.access_key = access_key
        self.secret_key = secret_key

        logger.debug(f"Creating new MinIO client for user: {access_key[:10]}...")

        # Always create a new client
        self.client = Minio(
            endpoint=settings.MINIO_URL.replace("http://", "").replace("https://", ""),
            access_key=access_key,
            secret_key=secret_key,
            secure=settings.MINIO_SSL
        )

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists"""
        return self.client.bucket_exists(bucket_name)

    def make_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket"""
        try:
            self.client.make_bucket(bucket_name)
            return True
        except Exception as e:
            logger.error(f"Error creating bucket {bucket_name}: {e}")
            return False

    def remove_bucket(self, bucket_name: str) -> bool:
        """Remove a bucket"""
        try:
            self.client.remove_bucket(bucket_name)
            return True
        except Exception as e:
            logger.error(f"Error removing bucket {bucket_name}: {e}")
            return False

    def list_objects(self, bucket_name: str, prefix: str = None, recursive: bool = False):
        """List objects in bucket"""
        return self.client.list_objects(bucket_name, prefix=prefix, recursive=recursive)

    def remove_object(self, bucket_name: str, object_name: str) -> bool:
        """Remove an object from bucket"""
        try:
            self.client.remove_object(bucket_name, object_name)
            return True
        except Exception as e:
            logger.error(f"Error removing object {object_name} from {bucket_name}: {e}")
            return False

    def get_url(self, bucket_name: str, object_name: str) -> str:
        """Get presigned URL to access an object"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            url = self.client.presigned_get_object(bucket_name=bucket_name, object_name=object_name)
            return url

        except Exception as e:
            logger.error(f"Error getting URL for {bucket_name}/{object_name}: {e}")
            return ""

    def upload_file(self, bucket_name: str, file: UploadFile, object_name: str) -> bool:
        """Upload a file to bucket"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file.file,
                length=file.size
            )
            return True

        except Exception as e:
            logger.error(f"Error uploading file to {bucket_name}: {e}")
            return False

    def upload_bytes(self, bucket_name: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        """Upload bytes data to bucket"""
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
            logger.error(f"Error uploading bytes to {bucket_name}/{object_name}: {e}")
            return False

    def delete_file(self, bucket_name: str, file_name: str) -> bool:
        """Delete a file from bucket"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            self.client.remove_object(bucket_name=bucket_name, object_name=file_name)
            return True

        except Exception as e:
            logger.error(f"Error deleting file {file_name} from {bucket_name}: {e}")
            return False

    def create_folder(self, bucket_name: str, folder_path: str) -> bool:
        """Create a folder in MinIO by creating an empty object with folder path"""
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
            logger.error(f"Error creating folder {folder_path} in {bucket_name}: {e}")
            return False

    def delete_folder(self, bucket_name: str, folder_path: str) -> bool:
        """Delete a folder and all its contents from MinIO"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'

            # List all objects in the folder
            objects = self.client.list_objects(bucket_name, prefix=folder_path, recursive=True)

            # Delete all objects in the folder
            for obj in objects:
                self.client.remove_object(bucket_name, obj.object_name)

            return True

        except Exception as e:
            logger.error(f"Error deleting folder {folder_path} from {bucket_name}: {e}")
            return False

    def rename_folder(self, bucket_name: str, old_path: str, new_path: str) -> bool:
        """Rename/move a folder by copying all objects to new path and deleting old ones"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            if old_path and not old_path.endswith('/'):
                old_path += '/'
            if new_path and not new_path.endswith('/'):
                new_path += '/'

            # List all objects in the old folder
            objects = list(self.client.list_objects(bucket_name, prefix=old_path, recursive=True))

            # Copy each object to new location
            for obj in objects:
                old_object_name = obj.object_name
                new_object_name = old_object_name.replace(old_path, new_path, 1)

                # Copy object
                copy_source = {"Bucket": bucket_name, "Key": old_object_name}
                self.client.copy_object(bucket_name, new_object_name, copy_source)

                # Delete old object
                self.client.remove_object(bucket_name, old_object_name)

            return True

        except Exception as e:
            logger.error(f"Error renaming folder from {old_path} to {new_path} in {bucket_name}: {e}")
            return False

    def move_folder(self, bucket_name: str, old_path: str, new_path: str) -> bool:
        """Move a folder (same as rename)"""
        return self.rename_folder(bucket_name, old_path, new_path)

    def list_files_in_folder(self, bucket_name: str, folder_path: str = "") -> list:
        """List all files in a specific folder"""
        try:
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket {bucket_name} does not exist")

            # Ensure folder_path format
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'
            elif folder_path == "/original":
                folder_path = ""

            # List objects with folder prefix, but not recursive to get only direct children
            objects = self.client.list_objects(bucket_name, prefix=folder_path, recursive=False)

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
            logger.error(f"Error listing files in folder {folder_path} from {bucket_name}: {e}")
            return []
