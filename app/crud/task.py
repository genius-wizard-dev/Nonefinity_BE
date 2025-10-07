from typing import Optional

from app.crud.base import BaseCRUD
from app.models.task import Task


class TaskCRUD(BaseCRUD[Task, Task, Task]):
    def __init__(self):
        super().__init__(Task)

    async def get_by_task_id(self, task_id: str) -> Optional[Task]:
        return await self.model.find_one({"task_id": task_id})


