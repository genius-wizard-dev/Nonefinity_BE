from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from typing import Optional

from app.services.user import user_service
from app.utils.api_response import ok
from app.utils.verify_token import verify_token
from app.utils.cache_decorator import cache_list
from app.crud.task import TaskCRUD
from beanie.odm.fields import PydanticObjectId


router = APIRouter()


async def _get_owner_id(current_user: dict) -> str:
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    return str(user.id)


@router.get("/", summary="List tasks", description="List tasks for current user")
@cache_list("tasks", ttl=300)  # Cache for 5 minutes
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    task_type: Optional[str] = Query(None, description="Filter by type: embedding|search"),
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(verify_token),
):
    owner_id = await _get_owner_id(current_user)
    crud = TaskCRUD()
    filter_ = {"user_id": owner_id}
    if status:
        filter_["status"] = status
    if task_type:
        filter_["task_type"] = task_type
    tasks = await crud.list(filter_, skip=skip, limit=min(limit, 100))
    data = jsonable_encoder(tasks, custom_encoder={PydanticObjectId: str})
    return ok(data=data, message="Tasks fetched")


