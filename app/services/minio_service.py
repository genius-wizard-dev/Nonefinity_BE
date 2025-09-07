import os
from minio import Minio, MinioAdmin
from minio.credentials import StaticProvider
from app.configs.settings import settings
from app.utils import get_logger
from fastapi import UploadFile
import tempfile
import json
logger = get_logger(__name__)


class MinIOService:
  def __init__(self, access_key: str = None, secret_key: str = None):

    if not settings.MINIO_ACCESS_KEY or not settings.MINIO_SECRET_KEY:
      raise ValueError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY not found in settings")

    # Admin client (user, policy, group…)
    self.admin = MinioAdmin(
      endpoint=settings.MINIO_URL.replace("http://", "").replace("https://", ""),
      credentials=StaticProvider(settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY),
      secure=settings.MINIO_URL.startswith("https://")
    )
    self.access_key = access_key
    self.secret_key = secret_key

    # S3 client (bucket, object…)
    self.client = Minio(
      endpoint=settings.MINIO_URL.replace("http://", "").replace("https://", ""),
      access_key=self.access_key or settings.MINIO_ACCESS_KEY,
      secret_key=self.secret_key or settings.MINIO_SECRET_KEY,
      secure=settings.MINIO_URL.startswith("https://")
    )

  def create_user(self, user_id: str, secret_key: str):
    """
    1. Create user
    2. Create bucket = user_id
    3. Create policy for bucket
    4. Assign policy to user
    """
    tmp_file_path = None
    try:
      # 1. Create user
      logger.info(f"Creating user {user_id}")
      self.admin.user_add(access_key=user_id, secret_key=secret_key)

      # 2. Create bucket
      if not self.client.bucket_exists(user_id):
        logger.info(f"Creating bucket {user_id}")
        self.client.make_bucket(user_id)

      # 3. Policy JSON
      policy_name = f"{user_id}-policy"
      policy_json = {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": [
              "s3:GetObject",
              "s3:PutObject",
              "s3:DeleteObject",
              "s3:ListBucket",
              "s3:GetBucketLocation",
            ],
            "Resource": [
              f"arn:aws:s3:::{user_id}",
              f"arn:aws:s3:::{user_id}/*"
            ]
          }
        ]
      }

      with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp_file:
          json.dump(policy_json, tmp_file, indent=2)
          tmp_file_path = tmp_file.name

      # 4. Create policy
      self.admin.policy_add(policy_name=policy_name, policy_file=tmp_file_path)

      # 5. Set policy for user
      self.admin.policy_set(policy_name=policy_name, user=user_id)

      return True

    except Exception as e:
      logger.error(f"Error creating user {user_id}: {e}")
      self.cleanup(user_id)
      raise

    finally:
      if tmp_file_path and os.path.exists(tmp_file_path):
        os.remove(tmp_file_path)

  def delete_user(self, user_id: str):
    """
    Delete user + policy + bucket
    """
    try:
      # Remove user
      logger.info(f"Removing user {user_id}")
      self.admin.user_remove(user_id)

      # Remove policy
      policy_name = f"{user_id}-policy"
      logger.info(f"Removing policy {policy_name}")
      self.admin.policy_remove(policy_name)

      # Remove bucket (if empty)
      if self.client.bucket_exists(user_id):
        objects = list(self.client.list_objects(user_id, recursive=True))
        if not objects:  # only delete if bucket is empty
          logger.info(f"Removing bucket {user_id}")
          self.client.remove_bucket(user_id)
        else:
          logger.warning(f"Bucket {user_id} is not empty, skipping removal")

      logger.info(f"User {user_id} deleted successfully")
      return True

    except Exception as e:
      logger.error(f"Error deleting user {user_id}: {e}")
      raise

  def cleanup(self, user_id: str):
    """
    Cleanup in case user creation fails (delete user + policy if any)
    """
    try:
      self.admin.user_remove(user_id)
    except Exception:
      pass
    try:
      self.admin.policy_remove(f"{user_id}-policy")
    except Exception:
      pass
    logger.info(f"Cleanup done for {user_id}")


  def get_url(self, bucket_name: str, object_name: str) -> str:
    """
    Get presigned URL to access an object
    """
    try:
      if not self.client.bucket_exists(bucket_name):
        raise ValueError(f"Bucket {bucket_name} does not exist")

      url = self.client.presigned_get_object(bucket_name=bucket_name, object_name=object_name)
      return url

    except Exception as e:
      logger.error(f"Error getting URL for {bucket_name}/{object_name}: {e}")
      return ""

  def upload_file(self, user_id: str, file: UploadFile, object_name: str) -> bool:
    """
    Upload a file to the user's bucket
    """
    try:
      if not self.client.bucket_exists(user_id):
        raise ValueError(f"Bucket {user_id} does not exist")

      self.client.put_object(
        bucket_name=user_id,
        object_name=object_name,
        data=file.file,
        length=file.size
      )
      return True

    except Exception as e:
      logger.error(f"Error uploading file to {user_id}: {e}")
      return False


  def delete_file(self, user_id: str, file_name: str) -> bool:
    """
    Delete a file from the user's bucket
    """
    try:
      if not self.client.bucket_exists(user_id):
        raise ValueError(f"Bucket {user_id} does not exist")

      self.client.remove_object(bucket_name=user_id, object_name=file_name)
      return True

    except Exception as e:
      logger.error(f"Error deleting file {file_name} from {user_id}: {e}")
      return False

  def create_folder(self, bucket_name: str, folder_path: str) -> bool:
    """
    Create a folder in MinIO by creating an empty object with folder path
    """
    try:
      if not self.client.bucket_exists(bucket_name):
        raise ValueError(f"Bucket {bucket_name} does not exist")

      # MinIO creates folders by having objects with path prefixes
      # We create an empty placeholder object to represent the folder
      if folder_path and not folder_path.endswith('/'):
        folder_path += '/'

      # Create empty object to represent folder
      from io import BytesIO
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
    """
    Delete a folder and all its contents from MinIO
    """
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
    """
    Rename/move a folder by copying all objects to new path and deleting old ones
    """
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
    """
    Move a folder (same as rename)
    """
    return self.rename_folder(bucket_name, old_path, new_path)

  def list_files_in_folder(self, bucket_name: str, folder_path: str = "") -> list:
    """
    List all files in a specific folder
    """
    try:
      if not self.client.bucket_exists(bucket_name):
        raise ValueError(f"Bucket {bucket_name} does not exist")

      # Ensure folder_path format
      if folder_path and not folder_path.endswith('/'):
        folder_path += '/'
      elif folder_path == "/":
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
