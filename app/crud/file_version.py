from app.crud.base import BaseCRUD
from app.models.file_version import FileVersion
from app.schemas.file_version import FileVersionCreate, FileVersionUpdate
from typing import List, Optional


class FileVersionCRUD(BaseCRUD[FileVersion, FileVersionCreate, FileVersionUpdate]):

    async def get_versions_by_raw_id(self, raw_id: str) -> List[FileVersion]:
        """Lấy tất cả versions của một file theo raw_id"""
        return await self.model.find({"raw_id": raw_id}).to_list()

    async def get_latest_version_by_raw_id(self, raw_id: str) -> Optional[FileVersion]:
        """Lấy version mới nhất của một file"""
        versions = await self.model.find({"raw_id": raw_id}).sort([("version", -1)]).limit(1).to_list()
        return versions[0] if versions else None

    async def get_version_by_raw_id_and_version(self, raw_id: str, version: int) -> Optional[FileVersion]:
        """Lấy một version cụ thể của file"""
        return await self.model.find_one({"raw_id": raw_id, "version": version})

    async def delete_versions_by_raw_id(self, raw_id: str, soft_delete: bool = True) -> bool:
        """Xóa tất cả versions của một file"""
        try:
            if soft_delete:
                # Soft delete: đánh dấu is_deleted = True
                from datetime import datetime
                update_data = {"is_deleted": True, "deleted_at": datetime.utcnow()}
                await self.model.find({"raw_id": raw_id}).update_many({"$set": update_data})
            else:
                # Hard delete: xóa hoàn toàn khỏi database
                await self.model.find({"raw_id": raw_id}).delete()
            return True
        except Exception as e:
            from app.utils import get_logger
            logger = get_logger(__name__)
            logger.error(f"Failed to delete versions for raw_id {raw_id}: {str(e)}")
            return False


file_version_crud = FileVersionCRUD(model=FileVersion)
