from app.services.minio_service import MinIOService
from fastapi import UploadFile
from app.schemas.file import FileCreate
from app.crud.file import FileCRUD
from typing import Optional
import mimetypes
import uuid
import os

class StorageService:

    def __init__(self, access_key: str, secret_key: str, crud: Optional[FileCRUD] = None):
        self._minio_service = MinIOService(access_key=access_key, secret_key=secret_key)
        self.crud = crud or FileCRUD()

    def _generate_unique_filename(self, original_filename: str) -> str:
        """Generate unique filename while preserving extension"""
        if not original_filename:
            return str(uuid.uuid4())

        # Split filename and extension
        _ , ext = os.path.splitext(original_filename)
        # Create unique filename: uuid_originalname.ext
        unique_name = f"{uuid.uuid4()}{ext}"
        return unique_name

    async def upload_file(self, user_id: str, file: UploadFile) -> Optional[FileCreate]:
      try:
          # Generate unique object name
          unique_object_name = self._generate_unique_filename(file.filename)
          content_type = file.content_type
          if content_type == "application/octet-stream" and file.filename:
            guessed_type, _ = mimetypes.guess_type(file.filename)
            if guessed_type:
              content_type = guessed_type

          file_info = FileCreate(
            bucket=user_id,
            file_name=file.filename,
            object_name=unique_object_name,
            file_size=file.size,
            file_type=content_type,
            owner_id=user_id
          )
          file_create = await self.crud.create(obj_in=file_info)
          if not file_create:
            return None

          upload = self._minio_service.upload_file(user_id=user_id, file=file, object_name=unique_object_name)
          if not upload:
            await self.crud.delete(file_create)
            return None

          url = self._minio_service.get_url(bucket_name=user_id, object_name=unique_object_name)
          file_create.url = url
          await file_create.save()
          return file_create

      except Exception:
        if 'file_create' in locals():
            await self.crud.delete(file_create)
        if 'unique_object_name' in locals():
            self._minio_service.delete_file(user_id=user_id, file_name=unique_object_name)
        return None

    async def delete_file(self, user_id: str, file_id: str) -> bool:
      file = await self.crud.get_by_id(file_id)
      if not file:
        return False

      deleted = self._minio_service.delete_file(user_id=user_id, file_name=file.object_name)
      if not deleted:
        return False

      await self.crud.delete(file)
      return True

    async def list_files(self, user_id: str) -> list[FileCreate]:
      files = await self.crud.list(filter_={"owner_id": user_id}, include_deleted=False)
      return files

