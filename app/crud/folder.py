from app.crud.base import BaseCRUD
from app.models.folder import Folder
from app.schemas import FolderCreate, FolderUpdate
from typing import List, Optional

class FolderCRUD(BaseCRUD[Folder, FolderCreate, FolderUpdate]):
    def __init__(self):
        super().__init__(Folder)

    async def get_by_path(self, owner_id: str, folder_path: str) -> Optional[Folder]:
        """Get folder by path"""
        return await self.model.find_one({
            "owner_id": owner_id,
            "folder_path": folder_path,
            "deleted_at": None
        })

    async def get_children(self, owner_id: str, parent_path: str) -> List[Folder]:
        """Get all folders under a parent path"""
        return await self.model.find({
            "owner_id": owner_id,
            "parent_path": parent_path,
            "deleted_at": None
        }).to_list()

    async def get_all_subfolders(self, owner_id: str, folder_path: str) -> List[Folder]:
        """Get all subfolders recursively under a folder path"""
        return await self.model.find({
            "owner_id": owner_id,
            "folder_path": {"$regex": f"^{folder_path.rstrip('/')}/"},
            "deleted_at": None
        }).to_list()

    async def search_folders_by_name(self, owner_id: str, search_term: str, limit: int = 50) -> List[Folder]:
        """Search folders by name pattern"""
        query = {
            "owner_id": owner_id,
            "folder_name": {"$regex": search_term, "$options": "i"},
            "deleted_at": None
        }
        return await self.model.find(query).limit(limit).to_list()

    async def count_subfolders(self, owner_id: str, parent_path: str) -> int:
        """Count direct subfolders under a parent path"""
        query = {
            "owner_id": owner_id,
            "parent_path": parent_path,
            "deleted_at": None
        }
        return await self.model.find(query).count()

    async def get_folder_tree(self, owner_id: str, root_path: str = "/") -> List[dict]:
        """Get folder tree structure starting from root_path"""
        folders = await self.model.find({
            "owner_id": owner_id,
            "deleted_at": None
        }).sort("folder_path").to_list()

        # Build tree structure
        tree = []
        folder_map = {}

        for folder in folders:
            folder_dict = {
                "id": str(folder.id),
                "name": folder.folder_name,
                "path": folder.folder_path,
                "parent_path": folder.parent_path,
                "children": []
            }
            folder_map[folder.folder_path] = folder_dict

            if folder.parent_path == root_path:
                tree.append(folder_dict)
            elif folder.parent_path in folder_map:
                folder_map[folder.parent_path]["children"].append(folder_dict)

        return tree
