from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.dataset_service import DatasetService
from app.services import user_service
from app.schemas.response import ApiResponse
from app.schemas.dataset import (
    FileToDatasetRequest,
    DatasetResponse,
    DatasetStats,
    DatasetDataResponse,
    DatasetUpdate
)
from starlette.status import HTTP_400_BAD_REQUEST
from app.core.exceptions import AppError
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from typing import List, Dict, Any

router = APIRouter()


@router.post("/convert", response_model=ApiResponse[DatasetResponse])
async def convert_file_to_dataset(
    request: FileToDatasetRequest,
    current_user=Depends(verify_token)
):
    """Convert CSV/Excel file to dataset

    Args:
        request: File to dataset conversion request
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)
    dataset_service = DatasetService(user_id=user_id, access_key=user_id, secret_key=user.minio_secret_key)

    try:
        result = await dataset_service.convert_file_to_dataset(
            user_id=user_id,
            file_id=request.file_id,
            dataset_name=request.dataset_name,
            description=request.description
        )

        if not result:
            raise AppError("Dataset conversion failed", status_code=HTTP_400_BAD_REQUEST)

        return created(result, message="Dataset created successfully")

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Conversion failed: {str(e)}")


@router.get("/list", response_model=ApiResponse[List[DatasetResponse]])
async def list_datasets(current_user=Depends(verify_token)):
    """List all datasets for current user

    Args:
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)
    dataset_service = DatasetService(user_id=user_id, access_key=user_id, secret_key=user.minio_secret_key)

    try:
        datasets = await dataset_service.list_datasets(user_id)
        return ok(data=datasets, message="Datasets retrieved successfully")

    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Failed to list datasets: {str(e)}")


@router.get("/{dataset_id}/data", response_model=ApiResponse[DatasetDataResponse])
async def get_dataset_data(
    dataset_id: str,
    offset: int = Query(0, ge=0, description="Starting row (offset)"),
    limit: int = Query(100, ge=1, le=10000, description="Number of rows to return"),
    current_user=Depends(verify_token)
):
    """Get data from dataset

    Args:
        dataset_id: Dataset ID
        offset: Starting row (offset)
        limit: Number of rows to return
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)
    dataset_service = DatasetService(user_id=user_id, access_key=user_id, secret_key=user.minio_secret_key)

    try:
        data = await dataset_service.get_dataset_data(
            user_id=user_id,
            dataset_id=dataset_id,
            offset=offset,
            limit=limit
        )

        return ok(data=data, message="Dataset data retrieved successfully")

    except AppError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Failed to get dataset data: {str(e)}")


@router.delete("/{dataset_id}", response_model=ApiResponse[bool])
async def delete_dataset(
    dataset_id: str,
    current_user=Depends(verify_token)
):
    """Delete dataset

    Args:
        dataset_id: Dataset ID
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)
    dataset_service = DatasetService(user_id=user_id, access_key=user_id, secret_key=user.minio_secret_key)

    try:
        success = await dataset_service.delete_dataset(user_id=user_id, dataset_id=dataset_id)

        if not success:
            raise AppError("Dataset deletion failed", status_code=HTTP_400_BAD_REQUEST)

        return ok(message="Dataset deleted successfully")

    except AppError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Failed to delete dataset: {str(e)}")


@router.put("/{dataset_id}/schema", response_model=ApiResponse[DatasetResponse])
async def update_dataset_schema(
    dataset_id: str,
    data_schema: List[Dict[str, Any]],
    current_user=Depends(verify_token)
):
    """Update dataset schema (column descriptions, etc.)

    Args:
        dataset_id: Dataset ID
        data_schema: New schema definition
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)
    dataset_service = DatasetService(user_id=user_id, access_key=user_id, secret_key=user.minio_secret_key)

    try:
        updated_dataset = await dataset_service.update_dataset_schema(
            user_id=user_id,
            dataset_id=dataset_id,
            new_schema=data_schema
        )

        if not updated_dataset:
            raise AppError("Schema update failed", status_code=HTTP_400_BAD_REQUEST)

        return ok(data=updated_dataset, message="Dataset schema updated successfully")

    except AppError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Failed to update schema: {str(e)}")


@router.get("/stats", response_model=ApiResponse[DatasetStats])
async def get_dataset_stats(current_user=Depends(verify_token)):
    """Get dataset statistics for current user

    Args:
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)
    dataset_service = DatasetService(user_id=user_id, access_key=user_id, secret_key=user.minio_secret_key)

    try:
        stats = await dataset_service.get_dataset_stats(user_id)
        return ok(data=stats, message="Dataset statistics retrieved successfully")

    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Failed to get dataset stats: {str(e)}")


@router.put("/{dataset_id}", response_model=ApiResponse[DatasetResponse])
async def update_dataset(
    dataset_id: str,
    update_data: DatasetUpdate,
    current_user=Depends(verify_token)
):
    """Update dataset information (name, description)

    Args:
        dataset_id: Dataset ID
        update_data: Update data
        current_user: Current user
    """
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)

    try:
        from app.crud.dataset import dataset_crud

        dataset = await dataset_crud.get_by_id(dataset_id)
        if not dataset or dataset.owner_id != user_id:
            raise AppError("Dataset not found or unauthorized", status_code=HTTP_400_BAD_REQUEST)

        updated_dataset = await dataset_crud.update(dataset, obj_in=update_data)
        return ok(data=updated_dataset, message="Dataset updated successfully")

    except AppError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Failed to update dataset: {str(e)}")
