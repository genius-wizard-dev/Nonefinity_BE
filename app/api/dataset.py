from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.status import HTTP_400_BAD_REQUEST

from app.services.dataset_service import DatasetService
from app.services import user_service
from app.core.exceptions import AppError
from app.utils.verify_token import verify_token
from app.utils.api_response import created, ok
from app.utils import get_logger
from app.schemas.dataset import (
   DatasetUpdate, DatasetUpdateRequest,
    DatasetCreateRequest, DatasetConvertRequest, DatasetQueryRequest,
    DatasetSchemaUpdateRequest, Dataset
)
from app.schemas.response import ApiResponse, ApiError

logger = get_logger(__name__)

router = APIRouter(
    prefix="/datasets",
    tags=["Datasets"],
    responses={
        400: {"model": ApiError, "description": "Bad Request"},
        401: {"model": ApiError, "description": "Unauthorized"},
        404: {"model": ApiError, "description": "Not Found"},
        422: {"model": ApiError, "description": "Validation Error"},
        500: {"model": ApiError, "description": "Internal Server Error"}
    }
)



async def get_user_and_service(current_user):
    """Helper function to get user and dataset service"""
    clerk_id = current_user.get("sub")
    user = await user_service.crud.get_by_clerk_id(clerk_id)
    if not user or not user.minio_secret_key:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="User not found")

    user_id = str(user.id)
    dataset_service = DatasetService(access_key=user_id, secret_key=user.minio_secret_key)

    return user_id, dataset_service


@router.post(
    "/create",
    response_model=ApiResponse[Dataset],
    status_code=status.HTTP_201_CREATED,
    summary="Create Dataset",
    description="Create a new dataset with defined schema",
    responses={
        201: {"description": "Dataset created successfully"},
        400: {"description": "Invalid request or schema validation error"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"}
    }
)
async def create_dataset(
    request: DatasetCreateRequest,
    current_user = Depends(verify_token)
):
    """
    Create a new dataset

    This endpoint creates a new dataset with a defined schema. The dataset can be used
    to store and query structured data.

    **Parameters:**
    - **dataset_name**: Name of the dataset (required)
    - **description**: Optional description of the dataset
    - **schema**: List of schema fields defining the table structure (required)

    **Schema Fields:**
    - **column_name**: Name of the column
    - **column_type**: Data type (string, integer, float, boolean, date, etc.)
    - **desc**: Optional column description
    - **old_name**: Optional old column name for renaming

    **Returns:**
    - Complete dataset information including ID and timestamps

    **Example:**
    ```json
    {
        "dataset_name": "Customer Data",
        "description": "Customer information dataset",
        "schema": [
            {
                "column_name": "customer_id",
                "column_type": "integer",
                "desc": "Unique customer identifier"
            },
            {
                "column_name": "name",
                "column_type": "string",
                "desc": "Customer full name"
            },
            {
                "column_name": "email",
                "column_type": "string",
                "desc": "Customer email address"
            }
        ]
    }
    ```

    **Note:**
    - Dataset names must be unique per user
    - Schema must contain at least one field
    - Column types must be valid SQL types
    """
    try:
        user_id, dataset_service = await get_user_and_service(current_user)
        result = await dataset_service.create_dataset(
            user_id,
            request.dataset_name,
            request.description,
            request.schema
        )
        return created(data=result, message="Dataset created successfully")
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Schema validation error: {str(e)}")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/convert")
async def convert(
    request: DatasetConvertRequest,
    current_user = Depends(verify_token)
):
    """Convert existing file in storage to dataset using file_id"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)

        result = await dataset_service.convert(
            user_id=user_id,
            file_id=request.file_id,
            dataset_name=request.dataset_name,
            description=request.description
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
    request: DatasetQueryRequest,
    current_user = Depends(verify_token)
):
    """Query dataset by ID with SQL validation and preprocessing"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)
        result = await dataset_service.query_dataset(user_id, request.query, request.limit)
        return ok(data=result, message="Query executed successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.error(f"Query dataset failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    update_data: DatasetUpdateRequest,
    current_user = Depends(verify_token)
):
    """Update dataset name and description only"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)

        # Convert to DatasetUpdate for service
        dataset_update = DatasetUpdate(
            name=update_data.name,
            description=update_data.description
        )

        await dataset_service.update_dataset(user_id, dataset_id, dataset_update)
        return ok(message="Dataset updated successfully")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Update dataset failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{dataset_id}/schema")
async def update_dataset_schema(
    dataset_id: str,
    request: DatasetSchemaUpdateRequest,
    current_user = Depends(verify_token)
):
    """Update dataset schema descriptions only"""
    try:
        logger.info(f"Updating schema for dataset {dataset_id}")
        logger.info(f"Received descriptions: {request.descriptions}")

        user_id, dataset_service = await get_user_and_service(current_user)
        await dataset_service.update_dataset_schema(user_id, dataset_id, request.descriptions)
        return ok(message="Dataset schema descriptions updated successfully")
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Validation error: {str(e)}")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Update dataset schema failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{dataset_id}/file-columns/{file_id}")
async def get_file_columns(
    dataset_id: str,
    file_id: str,
    current_user = Depends(verify_token)
):
    """Get file columns and dataset columns for mapping preparation"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)

        result = await dataset_service.get_file_and_dataset_columns(
            user_id=user_id,
            dataset_id=dataset_id,
            file_id=file_id
        )

        return ok(data=result, message="File and dataset columns retrieved successfully")

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Get file columns failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{dataset_id}/insert/{file_id}")
async def insert_data_from_file(
    dataset_id: str,
    file_id: str,
    current_user = Depends(verify_token)
):
    """Insert data from file into existing dataset with automatic column mapping"""
    try:
        user_id, dataset_service = await get_user_and_service(current_user)

        result = await dataset_service.insert_data_from_file(
            user_id=user_id,
            dataset_id=dataset_id,
            file_id=file_id
        )

        return created(data=result, message="Data inserted successfully from file")

    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Insert data from file failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

