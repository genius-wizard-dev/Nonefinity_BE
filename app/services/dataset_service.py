from app.services.minio_client_service import MinIOClientService
from app.services.duckdb_service import DuckDBService
from app.databases.duckdb import DuckDB
from app.schemas.dataset import DatasetCreate, DatasetUpdate
from app.crud.dataset import dataset_crud
from app.crud.file import FileCRUD
from app.core.exceptions import AppError
from app.utils import get_logger
from app.utils.file_classifier import FileClassifier
from typing import Optional, List, Dict, Any
import uuid
import os

logger = get_logger(__name__)


class DatasetService:
    """Service for handling dataset operations and file conversions"""

    def __init__(self, access_key: str, secret_key: str):
        self._minio_client = MinIOClientService(access_key=access_key, secret_key=secret_key)
        self.file_crud = FileCRUD()
        self.access_key = access_key
        self.secret_key = secret_key
        # Create DuckDB connection - no more pooling
        self._duckdb_conn = DuckDB(access_key=access_key, secret_key=secret_key)

    def _extract_unique_name_from_file_path(self, file_path: str) -> str:
        """Extract unique name from raw file path to use for parquet"""
        # file_path format: raw/{unique_name}.ext
        # Extract: {unique_name}
        filename_with_ext = os.path.basename(file_path)  # Get filename from path
        unique_name = os.path.splitext(filename_with_ext)[0]  # Remove extension
        return unique_name

    def _detect_schema_from_parquet(self, parquet_s3_path: str) -> List[Dict[str, Any]]:
        """Detect schema from parquet file using DuckDB"""
        try:
            # Use persistent connection
            schema_query = f"DESCRIBE SELECT * FROM read_parquet('{parquet_s3_path}') LIMIT 1"
            schema_result = self._duckdb_conn.execute(schema_query).fetchall()

            schema = []
            for row in schema_result:
                column_name = row[0]
                column_type = row[1]

                # Map DuckDB types to more user-friendly types (string, integer, float, boolean, date, datetime)
                type_mapping = {
                    'VARCHAR': 'string',
                    'INTEGER': 'integer',
                    'BIGINT': 'integer',
                    'DOUBLE': 'float',
                    'BOOLEAN': 'boolean',
                    'DATE': 'date',
                    'TIMESTAMP': 'datetime'
                }

                friendly_type = type_mapping.get(column_type.upper(), column_type.lower())

                schema.append({
                    "name": column_name,
                    "type": friendly_type,
                    "desc": None  # Will be filled by user later if needed (description)
                })

            return schema

        except Exception as e:
            logger.error(f"Failed to detect schema from parquet: {str(e)}")
            # Return empty schema if detection fails (empty list)
            return []

    def _get_parquet_stats(self, parquet_s3_path: str) -> Dict[str, Any]:
        """Get statistics from parquet file"""
        try:
            # Use persistent connection
            count_query = f"SELECT COUNT(*) FROM read_parquet('{parquet_s3_path}')"
            row_count = self._duckdb_conn.execute(count_query).fetchone()[0]

            return {
                "total_rows": row_count,
                "file_size": None  # Will be filled from MinIO separately (file size)
            }

        except Exception as e:
            logger.error(f"Failed to get parquet stats: {str(e)}")
            return {"total_rows": 0, "file_size": None}

    def _get_file_size_from_minio(self, user_id: str, object_name: str) -> Optional[int]:
        """Get file size from MinIO"""
        try:
            stat = self._minio_client.client.stat_object(user_id, object_name)
            return stat.size
        except Exception as e:
            logger.error(f"Failed to get file size from MinIO: {str(e)}")
            return None

    async def convert_file_to_dataset(
        self,
        user_id: str,
        file_id: str,
        dataset_name: str,
        description: Optional[str] = None
    ) -> Optional[DatasetCreate]:
        """Import CSV/Excel file to dataset with parquet in data/{folder}/ (data/{filename}.parquet)"""
        dataset_create = None
        dataset_folder = None
        parquet_object_name = None

        try:
            logger.info(f"Starting file to dataset conversion for user {user_id}, file_id: {file_id}")

            # Get source file
            file = await self.file_crud.get_by_id(file_id)
            if not file:
                raise AppError("Source file not found")

            if file.owner_id != user_id:
                raise AppError("Unauthorized: Cannot access file")

            # Check if file is CSV or Excel
            if not FileClassifier.is_csv_or_excel(file.file_type, file.file_ext):
                raise AppError("Only CSV and Excel files can be converted to datasets")

            # Check if dataset name already exists for this user
            existing_dataset = await dataset_crud.get_by_name_and_owner(dataset_name, user_id)
            if existing_dataset:
                raise AppError(f"Dataset with name '{dataset_name}' already exists")

            # Generate parquet path using same unique name as raw file
            unique_name = self._extract_unique_name_from_file_path(file.file_path)
            parquet_object_name = f"data/{unique_name}.parquet"

            # Create full S3 paths
            source_s3_path = f"s3://{user_id}/{file.file_path}"
            parquet_s3_path = f"s3://{user_id}/{parquet_object_name}"

            logger.info(f"Converting {file.file_path} to {parquet_object_name}")

            # Convert to Parquet based on file type
            conversion_success = False
            if file.file_ext.lower() == ".csv":
                conversion_success = await DuckDBService.convert_csv_to_parquet(
                    source_s3_path=source_s3_path,
                    parquet_s3_path=parquet_s3_path,
                    access_key=self.access_key,
                    secret_key=self.secret_key
                )
            else:
                conversion_success = await DuckDBService.convert_excel_to_parquet(
                    user_id=user_id,
                    excel_object_name=file.file_path,
                    parquet_s3_path=parquet_s3_path,
                    minio_client=self._minio_client
                )

            if not conversion_success:
                raise AppError(f"Failed to import {file.file_ext.upper()} file to Parquet format")

            # Detect schema from converted parquet
            schema = self._detect_schema_from_parquet(parquet_s3_path)
            if not schema:
                logger.warning("Could not detect schema, creating empty schema")
                schema = []

            # Get parquet statistics
            stats = self._get_parquet_stats(parquet_s3_path)

            # Get file size from MinIO
            parquet_file_size = self._get_file_size_from_minio(user_id, parquet_object_name)

            # Create dataset record
            dataset_info = DatasetCreate(
                name=dataset_name,
                description=description,
                owner_id=user_id,
                bucket=user_id,
                file_path=parquet_object_name,  # data/{filename}.parquet
                data_schema=schema,
                total_rows=stats.get("total_rows"),
                file_size=parquet_file_size,  # Get actual file size from MinIO
                source_file_id=file_id
            )

            dataset_create = await dataset_crud.create(obj_in=dataset_info)
            logger.info(f"Dataset created successfully: {dataset_create.id}")

            return dataset_create

        except Exception as e:
            logger.error(f"File to dataset conversion failed: {str(e)}")

            # Rollback operations
            rollback_errors = []

            # 1. Delete parquet file from MinIO
            if parquet_object_name:
                try:
                    parquet_deleted = self._minio_client.delete_file(
                        bucket_name=user_id,
                        file_name=parquet_object_name
                    )
                    if parquet_deleted:
                        logger.info(f"Rolled back parquet file: {parquet_object_name}")
                    else:
                        error_msg = f"Failed to delete parquet file: {parquet_object_name}"
                        logger.warning(error_msg)
                        rollback_errors.append(error_msg)
                except Exception as cleanup_error:
                    error_msg = f"Failed to cleanup parquet file: {cleanup_error}"
                    logger.error(error_msg)
                    rollback_errors.append(error_msg)

            # Note: No need to delete folder since we're using direct file path (data/{filename}.parquet)

            # 3. Delete database record
            if dataset_create:
                try:
                    await dataset_crud.delete(dataset_create, soft_delete=False)
                    logger.info(f"Rolled back dataset record: {dataset_create.id}")
                except Exception as cleanup_error:
                    error_msg = f"Failed to cleanup dataset record: {cleanup_error}"
                    logger.error(error_msg)
                    rollback_errors.append(error_msg)

            # Log rollback summary
            if rollback_errors:
                logger.error(f"Rollback completed with errors: {'; '.join(rollback_errors)}")
            else:
                logger.info("Complete rollback successful")

            # Re-raise original exception
            if isinstance(e, AppError):
                raise e
            else:
                raise AppError(f"Dataset conversion failed: {str(e)}")

    async def delete_dataset(self, user_id: str, dataset_id: str) -> bool:
        """Delete dataset and its parquet file"""
        try:
            logger.info(f"Starting dataset deletion for user {user_id}, dataset_id: {dataset_id}")

            dataset = await dataset_crud.get_by_id(dataset_id)
            if not dataset:
                raise AppError("Dataset not found")

            if dataset.owner_id != user_id:
                raise AppError("Unauthorized: Cannot delete dataset")

            deletion_errors = []

            # Delete parquet file from MinIO (file_path is now the full path)
            parquet_path = dataset.file_path
            try:
                parquet_deleted = self._minio_client.delete_file(bucket_name=user_id, file_name=parquet_path)
                if parquet_deleted:
                    logger.info(f"Deleted parquet file: {parquet_path}")
                else:
                    error_msg = f"Failed to delete parquet file: {parquet_path}"
                    logger.error(error_msg)
                    deletion_errors.append(error_msg)
            except Exception as e:
                error_msg = f"Failed to delete parquet file: {str(e)}"
                logger.error(error_msg)
                deletion_errors.append(error_msg)

            # Note: No need to delete folder since we're using direct file path (data/{filename}.parquet)

            # Delete database record
            try:
                await dataset_crud.delete(dataset, soft_delete=False)
                logger.info(f"Deleted dataset record: {dataset_id}")
            except Exception as e:
                error_msg = f"Failed to delete dataset record: {str(e)}"
                logger.error(error_msg)
                deletion_errors.append(error_msg)
                raise AppError("Failed to delete dataset record from database")

            if deletion_errors:
                logger.warning(f"Dataset deletion completed with some errors: {'; '.join(deletion_errors)}")
            else:
                logger.info(f"Dataset deleted successfully: {dataset_id}")

            return True

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Dataset deletion failed: {str(e)}")
            raise AppError(f"Deletion failed: {str(e)}")

    async def get_dataset_data(
        self,
        user_id: str,
        dataset_id: str,
        offset: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get data from dataset parquet file"""
        try:
            dataset = await dataset_crud.get_by_id(dataset_id)
            if not dataset or dataset.owner_id != user_id:
                raise AppError("Dataset not found or unauthorized")

            # Create full parquet path (file_path is now the full path) (data/{filename}.parquet)
            parquet_s3_path = f"s3://{user_id}/{dataset.file_path}"

            # Get data using DuckDB
            data = DuckDBService.get_data_from_parquet(
                parquet_s3_path=parquet_s3_path,
                offset=offset,
                limit=limit,
                access_key=self.access_key,
                secret_key=self.secret_key
            )

            return {
                "data": data,
                "total_rows": dataset.total_rows or 0,
                "schema": dataset.data_schema
            }

        except Exception as e:
            logger.error(f"Failed to get dataset data: {str(e)}")
            raise AppError(f"Failed to get dataset data: {str(e)}")

    async def list_datasets(self, user_id: str) -> List[DatasetCreate]:
        """List all datasets for user"""
        return await dataset_crud.get_by_owner_id(user_id)

    async def update_dataset_schema(
        self,
        user_id: str,
        dataset_id: str,
        new_schema: List[Dict[str, Any]]
    ) -> Optional[DatasetCreate]:
        """Update dataset schema (column descriptions, etc.)"""
        try:
            dataset = await dataset_crud.get_by_id(dataset_id)
            if not dataset or dataset.owner_id != user_id:
                raise AppError("Dataset not found or unauthorized")

            update_data = DatasetUpdate(data_schema=new_schema)
            updated_dataset = await dataset_crud.update(dataset, obj_in=update_data)

            logger.info(f"Updated dataset schema: {dataset_id}")
            return updated_dataset

        except Exception as e:
            logger.error(f"Failed to update dataset schema: {str(e)}")
            raise AppError(f"Failed to update schema: {str(e)}")

    async def get_dataset_stats(self, user_id: str) -> Dict[str, Any]:
        """Get dataset statistics for user"""
        return await dataset_crud.get_stats_by_owner(user_id)

    def close_connection(self):
        """Close DuckDB connection when not needed"""
        if hasattr(self, '_duckdb_conn'):
            self._duckdb_conn.close()

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.close_connection()


