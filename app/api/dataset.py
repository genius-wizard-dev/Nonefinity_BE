from fastapi import APIRouter, Depends, HTTPException, Form, Query
from pydantic import Field
from starlette.status import HTTP_400_BAD_REQUEST
from typing import Optional, List
import json

from app.services.dataset_service import DatasetService
from app.services import user_service
from app.core.exceptions import AppError
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from app.utils import get_logger
from app.schemas.dataset import DataSchemaField
logger = get_logger(__name__)
router = APIRouter()



async def get_user_and_service(current_user):
    """Helper function to get user and dataset service"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)
    dataset_service = DatasetService(access_key=user_id, secret_key=user.minio_secret_key)

    return user_id, dataset_service


@router.post("/create")
async def create_dataset(
    dataset_name: str = Form(...),
    description: Optional[str] = Form(None),
    schema: str = Form(...),
    current_user = Depends(verify_token)
):
    """Create a new dataset"""
    try:
        # Parse JSON string to List[DataSchemaField]
        schema_data = json.loads(schema)
        schema_fields = [DataSchemaField(**field) for field in schema_data]

        user_id, dataset_service = await get_user_and_service(current_user)
        result = await dataset_service.create_dataset(user_id, dataset_name, description, schema_fields)
        return created(data=result, message="Dataset created successfully")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Invalid JSON format in schema: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Schema validation error: {str(e)}")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/convert")
async def convert(
    file_id: str = Form(...),
    dataset_name: str = Form(...),
    description: Optional[str] = Form(None),
    current_user = Depends(verify_token)
):
    """Convert existing file in storage to dataset using file_id"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)

        result = await dataset_service.convert(
            user_id=user_id,
            file_id=file_id,
            dataset_name=dataset_name,
            description=description
        )

        return created(data=result, message="Dataset created from existing file successfully")

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.error(f"Convert existing file to dataset failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list")
async def list_dataset(
    current_user = Depends(verify_token),
    skip: int = Query(0),
    limit: int = Query(100)
):
    """List all datasets for user"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)
        result = await dataset_service.get_list_dataset(user_id, skip, limit)
        return ok(data=result, message="Datasets listed successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    current_user = Depends(verify_token)
):
    """Get dataset by ID"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)
        result = await dataset_service.get_dataset(user_id, dataset_id)
        return ok(data=result, message="Dataset retrieved successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    current_user = Depends(verify_token)
):
    """Delete dataset by ID"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)
        result = await dataset_service.delete_dataset(user_id, dataset_id)
        return ok(data=result, message="Dataset deleted successfully")

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.error(f"Delete dataset failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{dataset_id}/data")
async def get_dataset_data(
    dataset_id: str,
    current_user = Depends(verify_token),
    skip: int = Query(0),
    limit: int = Query(100)
):
    """Get dataset data by ID"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)
        result = await dataset_service.get_dataset_data(user_id, dataset_id, skip, limit)
        return ok(data=result, message="Dataset data retrieved successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.error(f"Get dataset data failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/query")
async def query_dataset(
    query: str = Form(...),
    limit: int = Form(100),
    current_user = Depends(verify_token)
):
    """Query dataset by ID with SQL validation and preprocessing"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)
        result = await dataset_service.query_dataset(user_id, query, limit)
        return ok(data=result, message="Query executed successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.error(f"Query dataset failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
