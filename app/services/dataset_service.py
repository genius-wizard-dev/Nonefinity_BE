from app.utils import get_logger
from app.databases.duckdb import DuckDB
from app.crud.dataset import DatasetCRUD
from app.crud.file import FileCRUD
from app.schemas.dataset import DatasetCreate, DataSchemaField
from app.core.exceptions import AppError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
from app.utils.preprocess_sql import check_sql_syntax, is_select_query, add_limit_sql
from typing import List

logger = get_logger(__name__)


class DatasetService:
    """Service for handling dataset operations with DuckLake"""

    def __init__(self, access_key: str, secret_key: str):
        """Initialize DatasetService with MinIO credentials"""
        self.access_key = access_key
        self.secret_key = secret_key
        self.crud = DatasetCRUD()
        self.file_crud = FileCRUD()
        self.duckdb = DuckDB(user_id=access_key, access_key=access_key, secret_key=secret_key)

    async def create_dataset(self, user_id: str, dataset_name: str, description: str, schema: List[DataSchemaField]):
      try:
        dataset = await self.crud.get_by_name(dataset_name, user_id)
        if dataset:
          raise AppError("Dataset already exists", status_code=HTTP_400_BAD_REQUEST)

        self.duckdb.execute(f"""CREATE TABLE IF NOT EXISTS {dataset_name}
                            (
                              {', '.join([f'{field.column_name} {field.column_type}' for field in schema])}
                            )
                            """)
        db_info = self.duckdb.execute(f"DESCRIBE {dataset_name}").df()

        # Create a mapping of column names to their descriptions from input schema
        schema_desc_map = {field.column_name: field.desc for field in schema if field.desc is not None}

        # Build column schemas preserving descriptions from input
        column_schemas = []
        for _, row in db_info.iterrows():
            column_name = row["column_name"]
            column_type = row["column_type"]
            column_desc = schema_desc_map.get(column_name)  # Get description from input schema if available

            column_schemas.append(DataSchemaField(
                column_name=column_name,
                column_type=column_type,
                desc=column_desc
            ))

        result = await self.crud.create_with_owner(user_id, DatasetCreate(name=dataset_name, description=description, data_schema=column_schemas))
        return result
      except Exception as e:
        logger.error(f"Error when creating dataset for user {user_id}: {str(e)}")
        raise AppError(f"Error when creating dataset: {str(e)}", status_code=HTTP_400_BAD_REQUEST)

    async def convert(
      self,
      user_id: str,
      file_id: str,
      dataset_name: str,
      description: str
    ):
      try:

        dataset = await self.crud.get_by_name(dataset_name, user_id)
        if dataset:
          raise AppError("Dataset already exists", status_code=HTTP_400_BAD_REQUEST)

        file = await self.file_crud.get_by_id(file_id)
        if not file:
          raise AppError("File not found", status_code=HTTP_404_NOT_FOUND)

        supported_csv_types = ["text/csv", "application/csv", "text/plain"]
        supported_excel_types = [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/vnd.ms-excel.sheet.macroEnabled.12",
            "application/vnd.ms-excel.template.macroEnabled.12",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.template"
        ]

        all_supported_types = supported_csv_types + supported_excel_types

        if file.file_type not in all_supported_types:
          raise AppError("File type not supported", status_code=HTTP_400_BAD_REQUEST)

        if file.file_type in supported_csv_types:
          data_schema = await self.convert_csv_to_dataset(user_id, file.file_path, dataset_name, description)
        elif file.file_type in supported_excel_types:
          data_schema = await self.convert_excel_to_dataset(user_id, file.file_path, dataset_name, description)

        result = await self.crud.create_with_owner(user_id, DatasetCreate(name=dataset_name, description=description, data_schema=data_schema))
        return result
      except Exception as e:
        logger.error(f"Error when converting file into dataset for user {user_id}: {str(e)}")
        raise AppError(f"Error when converting file into dataset: {str(e)}", status_code=HTTP_400_BAD_REQUEST)



    async def convert_csv_to_dataset(self, user_id: str, file_path: str, dataset_name: str, description: str):
        try:
            with self.duckdb as db:

                # Create table in DuckLake
                db.execute(f"CREATE TABLE {dataset_name} AS SELECT * FROM read_csv('s3://{user_id}/{file_path}', ignore_errors=true)")
                db_info = db.execute(f"DESCRIBE {dataset_name}").df()
                column_schemas = db_info[["column_name", "column_type"]].to_dict(orient="records")
                return column_schemas
        except Exception as e:
            logger.error(f"Error when converting CSV into dataset for user {user_id}: {str(e)}")
            raise AppError(f"Error when converting CSV into dataset: {str(e)}", status_code=HTTP_400_BAD_REQUEST)




    async def convert_excel_to_dataset(self, user_id: str, file_path: str, dataset_name: str, description: str):
      pass



    async def get_list_dataset(self, user_id: str, skip: int = 0, limit: int = 100):
        """Get list of datasets with auto-sync between DuckDB and MongoDB"""
        # Get all datasets for the user from MongoDB
        datasets = await self.crud.get_by_owner(user_id, skip, limit)
        available_datasets = []

        # Get all table names in DuckDB (single query)
        duckdb_tables = set(row[0] for row in self.duckdb.execute("SHOW TABLES").fetchall())

        # Early return if no datasets and no tables
        if not datasets and not duckdb_tables:
            return available_datasets

        # Sync datasets: create missing ones and update existing ones
        await self._sync_datasets_with_duckdb(user_id, datasets, duckdb_tables, available_datasets)

        return available_datasets

    def _schemas_different(self, mongodb_schema: List[DataSchemaField], duckdb_schema: List[DataSchemaField]) -> bool:
        """Compare two schemas to check if they are different (ignoring desc field)"""
        if len(mongodb_schema) != len(duckdb_schema):
            return True

        # Create dict for easier comparison (only compare column_name and column_type)
        mongodb_dict = {field.column_name: field.column_type for field in mongodb_schema}
        duckdb_dict = {field.column_name: field.column_type for field in duckdb_schema}

        # Compare column names
        if set(mongodb_dict.keys()) != set(duckdb_dict.keys()):
            return True

        # Compare column types (ignore desc field)
        for column_name in mongodb_dict:
            if mongodb_dict[column_name] != duckdb_dict[column_name]:
                return True

        return False

    async def _sync_datasets_with_duckdb(self, user_id: str, datasets: List, duckdb_tables: set, available_datasets: List):
        """Sync datasets between DuckDB and MongoDB"""
        # Get list of dataset names already in MongoDB
        existing_dataset_names = set(dataset.name for dataset in datasets)

        # Create datasets for tables that don't exist in MongoDB
        await self._create_missing_datasets(user_id, duckdb_tables, existing_dataset_names, available_datasets)

        # Check and sync existing datasets
        await self._sync_existing_datasets(datasets, duckdb_tables, available_datasets)

    async def _create_missing_datasets(self, user_id: str, duckdb_tables: set, existing_dataset_names: set, available_datasets: List):
        """Create datasets for tables that exist in DuckDB but not in MongoDB"""
        # Find tables that need to be created
        tables_to_create = [table_name for table_name in duckdb_tables if table_name not in existing_dataset_names]

        if not tables_to_create:
            return

        # Batch create datasets
        try:
            # Get schemas for all missing tables at once
            table_schemas = {}
            for table_name in tables_to_create:
                try:
                    columns_info = self.duckdb.execute(f"DESCRIBE {table_name}").df()
                    schema_data = columns_info[['column_name', 'column_type']].to_dict('records')
                    table_schemas[table_name] = schema_data
                except Exception as e:
                    logger.error(f"Error getting schema for table {table_name}: {str(e)}")
                    continue

            # Create datasets in batch
            for table_name, schema_data in table_schemas.items():
                try:
                    # Create schema fields
                    schema_fields = []
                    for col_info in schema_data:
                        schema_fields.append(DataSchemaField(
                            column_name=col_info['column_name'],
                            column_type=col_info['column_type'],
                            desc=None
                        ))

                    # Create dataset record in MongoDB
                    new_dataset = await self.crud.create_with_owner(
                        user_id,
                        DatasetCreate(
                            name=table_name,
                            description=f"Auto-created dataset for table {table_name}",
                            data_schema=schema_fields
                        )
                    )

                    # Get row count for new dataset
                    try:
                        row_count = self.duckdb.execute(f"SELECT COUNT(*) as count FROM {table_name}").df()["count"].iloc[0]
                        new_dataset_with_count = await self._add_row_count_to_dataset(new_dataset, row_count)
                        available_datasets.append(new_dataset_with_count)
                    except:
                        available_datasets.append(new_dataset)

                    logger.info(f"Auto-created dataset for table: {table_name}")
                except Exception as e:
                    logger.error(f"Error creating dataset for table {table_name}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error in batch dataset creation: {str(e)}")

    async def _sync_existing_datasets(self, datasets: List, duckdb_tables: set, available_datasets: List):
        """Sync existing datasets between DuckDB and MongoDB"""
        # Batch process: separate datasets that exist vs don't exist in DuckDB
        datasets_to_delete = []
        datasets_to_check = []

        for dataset in datasets:
            if dataset.name not in duckdb_tables:
                datasets_to_delete.append(dataset)
            else:
                datasets_to_check.append(dataset)

        # Batch delete datasets that don't exist in DuckDB
        if datasets_to_delete:
            for dataset in datasets_to_delete:
                await self.crud.delete(dataset)
                logger.info(f"Deleted dataset {dataset.name} - table not found in DuckDB")

        # Batch get all schemas from DuckDB at once
        if datasets_to_check:
            await self._batch_sync_schemas(datasets_to_check, available_datasets)

    async def _batch_sync_schemas(self, datasets: List, available_datasets: List):
        """Batch sync schemas for multiple datasets"""
        # Get all table schemas and row counts in one go
        try:
            # Create a single query to get all table schemas and row counts
            table_names = [dataset.name for dataset in datasets]
            all_schemas = {}
            row_counts = {}

            for table_name in table_names:
                try:
                    # Get schema
                    columns_info = self.duckdb.execute(f"DESCRIBE {table_name}").df()
                    schema_data = columns_info[['column_name', 'column_type']].to_dict('records')
                    all_schemas[table_name] = schema_data

                    # Get row count
                    row_count = self.duckdb.execute(f"SELECT COUNT(*) as count FROM {table_name}").df()["count"].iloc[0]
                    row_counts[table_name] = row_count

                except Exception as e:
                    logger.error(f"Error getting schema/count for table {table_name}: {str(e)}")
                    all_schemas[table_name] = []
                    row_counts[table_name] = 0

            # Process each dataset
            for dataset in datasets:
                try:
                    if dataset.name not in all_schemas or not all_schemas[dataset.name]:
                        # Add row count to dataset even if schema sync fails
                        dataset_with_count = await self._add_row_count_to_dataset(dataset, row_counts.get(dataset.name, 0))
                        available_datasets.append(dataset_with_count)
                        continue

                    # Create current schema fields from DuckDB
                    current_schema_fields = []
                    for col_info in all_schemas[dataset.name]:
                        current_schema_fields.append(DataSchemaField(
                            column_name=col_info['column_name'],
                            column_type=col_info['column_type'],
                            desc=None
                        ))

                    # Convert MongoDB schema to DataSchemaField objects
                    mongodb_schema_fields = []
                    for schema_dict in dataset.data_schema:
                        mongodb_schema_fields.append(DataSchemaField(
                            column_name=schema_dict['column_name'],
                            column_type=schema_dict['column_type'],
                            desc=schema_dict.get('desc')
                        ))

                    # Compare schemas
                    if self._schemas_different(mongodb_schema_fields, current_schema_fields):
                        # Create updated schema with preserved descriptions
                        updated_schema_fields = []
                        for current_field in current_schema_fields:
                            existing_field = next(
                                (f for f in mongodb_schema_fields if f.column_name == current_field.column_name),
                                None
                            )

                            desc = existing_field.desc if existing_field else None

                            updated_schema_fields.append(DataSchemaField(
                                column_name=current_field.column_name,
                                column_type=current_field.column_type,
                                desc=desc
                            ))

                        # Update schema in MongoDB
                        updated_dataset = await self.crud.update_schema(dataset.id, updated_schema_fields)
                        # Add row count to updated dataset
                        updated_dataset_with_count = await self._add_row_count_to_dataset(updated_dataset, row_counts.get(dataset.name, 0))
                        available_datasets.append(updated_dataset_with_count)
                        logger.info(f"Updated schema for dataset: {dataset.name}")
                    else:
                        # Add row count to existing dataset
                        dataset_with_count = await self._add_row_count_to_dataset(dataset, row_counts.get(dataset.name, 0))
                        available_datasets.append(dataset_with_count)

                except Exception as e:
                    logger.error(f"Error processing dataset {dataset.name}: {str(e)}")
                    # Add row count even if there's an error
                    dataset_with_count = await self._add_row_count_to_dataset(dataset, row_counts.get(dataset.name, 0))
                    available_datasets.append(dataset_with_count)

        except Exception as e:
            logger.error(f"Error in batch schema sync: {str(e)}")
            # Fallback: add all datasets without sync but with row counts
            for dataset in datasets:
                try:
                    row_count = self.duckdb.execute(f"SELECT COUNT(*) as count FROM {dataset.name}").df()["count"].iloc[0]
                    dataset_with_count = await self._add_row_count_to_dataset(dataset, row_count)
                    available_datasets.append(dataset_with_count)
                except:
                    available_datasets.append(dataset)

    async def _add_row_count_to_dataset(self, dataset, row_count: int):
        """Add row count to dataset object"""
        # Convert dataset to dict and add row_count
        if hasattr(dataset, 'model_dump'):
            dataset_dict = dataset.model_dump(mode='json')
        else:
            dataset_dict = dataset.__dict__.copy()
            # Convert ObjectId to string manually
            for key, value in dataset_dict.items():
                if hasattr(value, '__str__') and 'ObjectId' in str(type(value)):
                    dataset_dict[key] = str(value)

        dataset_dict['row_count'] = int(row_count)

        # Return dict instead of SimpleNamespace to avoid serialization issues
        return dataset_dict

    async def sync_dataset_schema(self, user_id: str, dataset_name: str):
        """Manually sync a specific dataset schema"""
        try:
            # Get dataset from MongoDB
            dataset = await self.crud.get_by_name(dataset_name, user_id)
            if not dataset:
                logger.warning(f"Dataset {dataset_name} not found in MongoDB")
                return None

            # Get current schema from DuckDB
            current_columns_info = self.duckdb.execute(f"DESCRIBE {dataset_name}").df()
            current_schema_data = current_columns_info[['column_name', 'column_type']].to_dict('records')

            # Create current schema fields
            current_schema_fields = []
            for col_info in current_schema_data:
                current_schema_fields.append(DataSchemaField(
                    column_name=col_info['column_name'],
                    column_type=col_info['column_type'],
                    desc=None
                ))

            # Convert MongoDB schema to DataSchemaField objects
            mongodb_schema_fields = []
            for schema_dict in dataset.data_schema:
                mongodb_schema_fields.append(DataSchemaField(
                    column_name=schema_dict['column_name'],
                    column_type=schema_dict['column_type'],
                    desc=schema_dict.get('desc')
                ))

            # Compare and update if needed
            if self._schemas_different(mongodb_schema_fields, current_schema_fields):
                # Create new schema with description from MongoDB
                updated_schema_fields = []
                for current_field in current_schema_fields:
                    existing_field = next(
                        (f for f in mongodb_schema_fields if f.column_name == current_field.column_name),
                        None
                    )
                    desc = existing_field.desc if existing_field else None

                    updated_schema_fields.append(DataSchemaField(
                        column_name=current_field.column_name,
                        column_type=current_field.column_type,
                        desc=desc
                    ))

                # Update schema in MongoDB
                updated_dataset = await self.crud.update_schema(dataset.id, updated_schema_fields)
                logger.info(f"Synced schema for dataset: {dataset_name}")
                return updated_dataset
            else:
                logger.info(f"Schema for dataset {dataset_name} is already up to date")
                return dataset

        except Exception as e:
            logger.error(f"Error syncing schema for dataset {dataset_name}: {str(e)}")
            return None

    async def get_dataset(self, user_id: str, dataset_id: str):
      dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
      if not dataset:
        raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

      with self.duckdb as db:
        duckdb_tables = set(row[0] for row in db.execute("SHOW TABLES").fetchall())
        if dataset.name not in duckdb_tables:
          await self.crud.delete(dataset)
          raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)
      return dataset

    async def delete_dataset(self, user_id: str, dataset_id: str):
      dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
      if not dataset:
        raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

      try:
        with self.duckdb as db:
          db.execute(f"DROP TABLE {dataset.name}")
          logger.info(f"Deleted dataset: {dataset.name} for user {user_id}")
      except Exception as e:
        logger.error(f"Error when deleting dataset for user {user_id}: {str(e)}")
        raise AppError(f"Error when deleting dataset: {str(e)}", status_code=HTTP_400_BAD_REQUEST)

      await self.crud.delete(dataset)
      return True


    async def get_dataset_data(self, user_id: str, dataset_id: str, skip: int = 0, limit: int = 100):
      dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
      if not dataset:
        raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

      try:
        with self.duckdb as db:
          data = db.execute(f"SELECT * FROM {dataset.name} LIMIT {limit} OFFSET {skip}").df()
          if data.empty:
            return {
              "data": [],
              "total_rows": 0,
              "offset": skip,
              "limit": limit
            }
          return {
            "data": data.to_dict(orient="records"),
            "total_rows": data.shape[0],
            "offset": skip,
            "limit": limit
          }
      except Exception as e:
        logger.error(f"Error when getting dataset data for user {user_id}: {str(e)}")
        raise AppError(f"Error when getting dataset data: {str(e)}", status_code=HTTP_400_BAD_REQUEST)

    async def query_dataset(self, user_id: str, query: str, limit: int = 100):
        """Execute SQL query on dataset with validation and preprocessing"""

        try:
            # Validate SQL syntax
            if not check_sql_syntax(query):
                raise AppError("Invalid SQL syntax", status_code=HTTP_400_BAD_REQUEST)

            # Check if it's a SELECT query
            # if not is_select_query(query):
            #     raise AppError("Only SELECT queries are allowed", status_code=HTTP_400_BAD_REQUEST)

            # Add limit to query if not present
            processed_query = add_limit_sql(query, limit)
            data = self.duckdb.execute(processed_query).df()
            return data.to_dict('records')

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error when querying dataset for user {user_id}: {str(e)}")
            # Remove "Catalog Error:" prefix from error message
            error_message = str(e)
            if error_message.startswith("Catalog Error:"):
                error_message = error_message.replace("Catalog Error:", "").strip()
            raise AppError(f"Error when querying dataset: {error_message}", status_code=HTTP_400_BAD_REQUEST)
