from app.crud.base import BaseCRUD
from app.models.file import File
from app.schemas.file import FileCreate, FileUpdate
from typing import List, Optional


class FileCRUD(BaseCRUD[File, FileCreate, FileUpdate]):
    def __init__(self):
        super().__init__(File)

    async def get_by_object_name(self, owner_id: str, object_name: str) -> Optional[File]:
        """Get file by object name"""
        return await self.model.find_one({
            "owner_id": owner_id,
            "object_name": object_name,
            "deleted_at": None
        })

    async def get_files_in_folder(self, owner_id: str, folder_path: str, include_deleted: bool = False) -> List[File]:
        """Get all files in a specific folder"""
        query = {
            "owner_id": owner_id,
            "folder_path": folder_path
        }
        if not include_deleted:
            query["deleted_at"] = None

        return await self.model.find(query).to_list()

    async def search_files_by_name(self, owner_id: str, search_term: str, limit: int = 50) -> List[File]:
        """Search files by name pattern"""
        query = {
            "owner_id": owner_id,
            "file_name": {"$regex": search_term, "$options": "i"},
            "deleted_at": None
        }
        return await self.model.find(query).limit(limit).to_list()

    async def get_files_by_type(self, owner_id: str, file_type: str, limit: int = 50) -> List[File]:
        """Get files by file type"""
        query = {
            "owner_id": owner_id,
            "file_type": {"$regex": f"^{file_type}", "$options": "i"},
            "deleted_at": None
        }
        return await self.model.find(query).limit(limit).to_list()

    async def count_files_in_folder(self, owner_id: str, folder_path: str) -> int:
        """Count files in a specific folder"""
        query = {
            "owner_id": owner_id,
            "folder_path": folder_path,
            "deleted_at": None
        }
        return await self.model.find(query).count()

    async def get_total_size_in_folder(self, owner_id: str, folder_path: str) -> int:
        """Get total size of files in a folder"""
        pipeline = [
            {
                "$match": {
                    "owner_id": owner_id,
                    "folder_path": folder_path,
                    "deleted_at": None,
                    "file_size": {"$exists": True, "$ne": None}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_size": {"$sum": "$file_size"}
                }
            }
        ]

        result = await self.model.get_pymongo_collection().aggregate(pipeline).to_list()
        return result[0]["total_size"] if result else 0



