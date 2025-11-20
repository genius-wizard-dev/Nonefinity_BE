from app.crud.base import BaseCRUD
from app.models.file import File
from app.schemas.file import FileCreate, FileUpdate
from typing import List, Optional


class FileCRUD(BaseCRUD[File, FileCreate, FileUpdate]):
    def __init__(self):
        super().__init__(File)

    async def get_by_file_path(self, owner_id: str, file_path: str) -> Optional[File]:
        """Get file by file path"""
        return await self.model.find_one({
            "owner_id": owner_id,
            "file_path": file_path
        })

    async def search_files_by_name(self, owner_id: str, search_term: str, limit: int = 50) -> List[File]:
        """Search files by name pattern"""
        query = {
            "owner_id": owner_id,
            "file_name": {"$regex": search_term, "$options": "i"}
        }
        return await self.model.find(query).limit(limit).to_list()

    async def get_files_by_type(self, owner_id: str, file_type: str, limit: int = 50) -> List[File]:
        """Get files by file type"""
        query = {
            "owner_id": owner_id,
            "file_type": {"$regex": f"^{file_type}", "$options": "i"}
        }
        return await self.model.find(query).limit(limit).to_list()

    async def count_files(self, owner_id: str) -> int:
        """Count all files for user"""
        query = {"owner_id": owner_id}
        return await self.model.find(query).count()

    async def get_total_size(self, owner_id: str) -> int:
        """Get total size of all files for user"""
        pipeline = [
            {
                "$match": {
                    "owner_id": owner_id,
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


file_crud = FileCRUD()
