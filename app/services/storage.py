from app.services.minio_service import MinIOService
from fastapi import UploadFile

class StorageService:

    def __init__(self, access_key: str, secret_key: str):
        self.minio_service = MinIOService(access_key=access_key, secret_key=secret_key)

    def upload_file(self, user_id: str, file: UploadFile):
        return self.minio_service.upload_file(user_id=user_id, file=file)
