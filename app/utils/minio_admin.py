import subprocess
import os
import json
from app.configs.settings import settings
from app.utils import get_logger

logger = get_logger(__name__)

def run_cmd(cmd: str):
    """Helper run command shell"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed: {result.stderr}")
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def create_minio_user(user_id: str, secret_key: str) -> dict:
    """
    1. Create user (access_key = user_id, secret_key)
    2. Create bucket named = user_id
    3. Create policy allowing user access only to this bucket
    4. Attach policy to user
    """
    policy_file = None

    try:
        # 1. Create user
        run_cmd(f"mc admin user add {settings.MINIO_ALIAS} {user_id} {secret_key}")

        # 2. Create bucket
        run_cmd(f"mc mb {settings.MINIO_ALIAS}/{user_id}")

        # 3. Create policy JSON
        policy_name = f"{user_id}-policy"
        policy_file = f"/tmp/{policy_name}.json"

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
                        "s3:GetBucketLocation"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{user_id}",
                        f"arn:aws:s3:::{user_id}/*"
                    ]
                }
            ]
        }

        with open(policy_file, "w") as f:
            json.dump(policy_json, f, indent=2)

        # 4. Create policy in MinIO
        run_cmd(f"mc admin policy create {settings.MINIO_ALIAS} {policy_name} {policy_file}")

        # 5. Attach policy to user
        run_cmd(f"mc admin policy attach {settings.MINIO_ALIAS} {policy_name} --user {user_id}")

        return {
            "user_id": user_id,
            "bucket": user_id,
            "policy": policy_name,
            "status": "User created successfully"
        }

    except Exception as e:
        logger.error(f"Error creating user resources: {e}")
        # Cleanup on error
        try:
            if  user_id:
                run_cmd(f"mc admin user remove {settings.MINIO_ALIAS} {user_id}")
        except:
            pass

        try:
            policy_name = f"{user_id}-policy"
            run_cmd(f"mc admin policy remove {settings.MINIO_ALIAS} {policy_name}")
        except:
            pass

        raise RuntimeError(f"Failed to create user resources: {str(e)}")

    finally:
        # Cleanup temp file
        if policy_file and os.path.exists(policy_file):
            try:
                os.remove(policy_file)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {policy_file}: {e}")

