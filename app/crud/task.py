from typing import Optional, List

from app.crud.base import BaseCRUD
from app.models.task import Task


class TaskCRUD(BaseCRUD[Task, Task, Task]):
    def __init__(self):
        super().__init__(Task)

    async def get_by_task_id(self, task_id: str) -> Optional[Task]:
        return await self.model.find_one({"task_id": task_id})

    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 50) -> List[Task]:
        """Get all tasks for a user with pagination"""
        return await self.model.find({"user_id": user_id}).skip(skip).limit(limit).to_list()

    async def count_by_user_id(self, user_id: str) -> int:
        """Count total tasks for a user"""
        return await self.model.find({"user_id": user_id}).count()

    async def delete_by_knowledge_store_id(self, knowledge_store_id: str, user_id: str) -> int:
        """Delete all tasks for a specific knowledge store"""
        result = await self.model.find(
            {"knowledge_store_id": knowledge_store_id, "user_id": user_id}
        ).delete()
        return result.deleted_count if result else 0

    async def update_status(self, task_id: str, update_data: dict) -> bool:
        """Update task status by MongoDB ObjectId"""
        task = await self.get_by_id(task_id)
        if not task:
            return False
        await task.set(update_data)
        return True


task_crud = TaskCRUD()


