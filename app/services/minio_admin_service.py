import os
from minio import MinioAdmin
from minio.credentials import StaticProvider
from app.configs.settings import settings
from app.utils import get_logger
from app.services.minio_client_service import MinIOClientService
import tempfile
import json

logger = get_logger(__name__)

class MinIOAdminService:
    def __init__(self):
        if not settings.MINIO_ACCESS_KEY or not settings.MINIO_SECRET_KEY:
            raise ValueError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY not found in settings")

        # Admin client (user, policy, group…)
        self.admin = MinioAdmin(
            endpoint=settings.MINIO_URL.replace("http://", "").replace("https://", ""),
            credentials=StaticProvider(settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY),
            secure=settings.MINIO_SSL
        )
        self._minio_client = MinIOClientService(
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY
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

            if not self._minio_client.bucket_exists(user_id):
                logger.info(f"Creating bucket {user_id}")
                self._minio_client.make_bucket(user_id)

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
        from .minio_client_service import MinIOClientService

        try:
            # Remove user
            logger.info(f"Removing user {user_id}")
            self.admin.user_remove(user_id)

            # Remove policy
            policy_name = f"{user_id}-policy"
            logger.info(f"Removing policy {policy_name}")
            self.admin.policy_remove(policy_name)

            # Remove bucket (if empty) using admin client
            admin_client = MinIOClientService()
            if admin_client.bucket_exists(user_id):
                objects = list(admin_client.list_objects(user_id, recursive=True))
                if not objects:  # only delete if bucket is empty
                    logger.info(f"Removing bucket {user_id}")
                    admin_client.remove_bucket(user_id)
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

minio_admin_service = MinIOAdminService()
