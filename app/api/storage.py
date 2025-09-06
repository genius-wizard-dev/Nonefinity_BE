from fastapi import APIRouter,  UploadFile
from app.services import StorageService, user_service
router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile):

    user_id = "68bbed17a5cc02a35ac0e0fd"
    user = await user_service.crud.get_by_id(user_id)
    if not user:
        return {"status": "failed", "reason": "User not found"}

    storage_service = StorageService( access_key=user_id, secret_key=user.minio_secret_key)

    result = storage_service.upload_file(user_id=user_id, file=file)
    return {"status": "success", "data": result}


