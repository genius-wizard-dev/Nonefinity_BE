from app.utils import get_logger
from app.databases.duckdb import DuckDB, DuckDBLockError
from app.schemas.dataset import DatasetCreate, DataSchemaField, DatasetUpdate
from app.core.exceptions import AppError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST, HTTP_503_SERVICE_UNAVAILABLE
from app.utils.preprocess_sql import check_sql_syntax, add_limit_sql, is_schema_modifying_query, extract_table_names_from_query
from typing import List, Dict
from app.crud import file_crud, dataset_crud
logger = get_logger(__name__)


class DatasetService:
    """Service for handling dataset operations with DuckLake"""

    def __init__(self, access_key: str, secret_key: str):
        """Initialize DatasetService with MinIO credentials"""
        self.access_key = access_key
        self.secret_key = secret_key
        self.crud = dataset_crud
        self.file_crud = file_crud
        self.duckdb = DuckDB(user_id=access_key, access_key=access_key, secret_key=secret_key)

    async def create_dataset(self, user_id: str, dataset_name: str, description: str, schema: List[DataSchemaField]):
      try:
        dataset = await self.crud.get_by_name(dataset_name, user_id)
        if dataset:
          raise AppError("Dataset already exists", status_code=HTTP_400_BAD_REQUEST)

        await self.duckdb.async_execute(f"""CREATE TABLE IF NOT EXISTS {dataset_name}
                            (
                              {', '.join([f'{field.column_name} {field.column_type}' for field in schema])}
                            )
                            """)
        db_info = await self.duckdb.async_query(f"DESCRIBE {dataset_name}")

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
            # Create table in DuckLake
            await self.duckdb.async_execute(f"CREATE TABLE {dataset_name} AS SELECT * FROM read_csv('s3://{user_id}/{file_path}')")
            db_info = await self.duckdb.async_query(f"DESCRIBE {dataset_name}")
            column_schemas = db_info[["column_name", "column_type"]].to_dict(orient="records")
            return column_schemas
        except Exception as e:
            logger.error(f"Error when converting CSV into dataset for user {user_id}: {str(e)}")
            raise AppError(f"Error when converting CSV into dataset: {str(e)}", status_code=HTTP_400_BAD_REQUEST)




    async def convert_excel_to_dataset(self, user_id: str, file_path: str, dataset_name: str, description: str):
        try:
          # Create table in DuckLake
          await self.duckdb.async_execute(f"CREATE TABLE {dataset_name} AS SELECT * FROM read_xlsx('s3://{user_id}/{file_path}')")
          db_info = await self.duckdb.async_query(f"DESCRIBE {dataset_name}")
          column_schemas = db_info[["column_name", "column_type"]].to_dict(orient="records")
          return column_schemas
        except Exception as e:
          logger.error(f"Error when converting Excel into dataset for user {user_id}: {str(e)}")
          raise AppError(f"Error when converting Excel into dataset: {str(e)}", status_code=HTTP_400_BAD_REQUEST)



    async def get_list_dataset(self, user_id: str, skip: int = 0, limit: int = 100):
        """Get list of datasets with auto-sync between DuckDB and MongoDB"""
        # Get all datasets for the user from MongoDB
        datasets = await self.crud.get_by_owner(user_id, skip, limit)
        available_datasets = []

        # Get all table names in DuckDB (single query)
        result = await self.duckdb.async_execute("SHOW TABLES")
        duckdb_tables = set(row[0] for row in result.fetchall())

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

    def _smart_match_columns(self, mongodb_schema: List[DataSchemaField], duckdb_schema: List[DataSchemaField]) -> Dict[str, str]:
        """
        Smart column matching to preserve descriptions when column names change.
        Uses multiple strategies:
        1. Exact name match
        2. Position-based match (if same count and types match)
        3. Type-based match (if unique type)

        Returns:
            Dict mapping new_column_name -> old_column_name (for description preservation)
        """
        column_mapping = {}

        # Strategy 1: Exact name match
        mongodb_dict = {field.column_name: field for field in mongodb_schema}
        duckdb_dict = {field.column_name: field for field in duckdb_schema}

        for new_col_name, new_col_field in duckdb_dict.items():
            if new_col_name in mongodb_dict:
                # Exact match found
                column_mapping[new_col_name] = new_col_name
            else:
                # No exact match, try position-based matching
                column_mapping[new_col_name] = None

        # Strategy 2: Position-based matching (if same count and types match)
        if len(mongodb_schema) == len(duckdb_schema):
            for i, (new_col, old_col) in enumerate(zip(duckdb_schema, mongodb_schema)):
                if column_mapping.get(new_col.column_name) is None:
                    # Check if types match (allowing for some type variations)
                    if self._types_compatible(old_col.column_type, new_col.column_type):
                        column_mapping[new_col.column_name] = old_col.column_name

        # Strategy 3: Type-based matching for unmatched columns
        unmatched_new = [col for col in duckdb_schema if column_mapping.get(col.column_name) is None]
        unmatched_old = [col for col in mongodb_schema if col.column_name not in column_mapping.values()]

        for new_col in unmatched_new:
            # Find old column with same type
            for old_col in unmatched_old:
                if self._types_compatible(old_col.column_type, new_col.column_type):
                    # Check if this type is unique in both schemas
                    new_type_count = sum(1 for c in duckdb_schema if c.column_type == new_col.column_type)
                    old_type_count = sum(1 for c in mongodb_schema if c.column_type == old_col.column_type)

                    if new_type_count == 1 and old_type_count == 1:
                        column_mapping[new_col.column_name] = old_col.column_name
                        unmatched_old.remove(old_col)
                        break

        return column_mapping

    def _types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two column types are compatible"""
        type1_lower = type1.lower() if type1 else ""
        type2_lower = type2.lower() if type2 else ""

        # Exact match
        if type1_lower == type2_lower:
            return True

        # Numeric types compatibility
        numeric_types = ['integer', 'bigint', 'smallint', 'tinyint', 'float', 'double', 'decimal', 'numeric']
        if type1_lower in numeric_types and type2_lower in numeric_types:
            return True

        # String types compatibility
        string_types = ['string', 'varchar', 'text', 'char']
        if type1_lower in string_types and type2_lower in string_types:
            return True

        # Date/time types compatibility
        datetime_types = ['date', 'timestamp', 'datetime']
        if type1_lower in datetime_types and type2_lower in datetime_types:
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
                    columns_info = await self.duckdb.async_query(f"DESCRIBE {table_name}")
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
                        row_count_df = await self.duckdb.async_query(f"SELECT COUNT(*) as count FROM {table_name}")
                        row_count = row_count_df["count"].iloc[0]
                        new_dataset_with_count = await self._add_row_count_to_dataset(new_dataset, row_count)
                        available_datasets.append(new_dataset_with_count)
                    except Exception:
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
        """Batch sync schemas for multiple datasets with smart column matching"""
        # Get all table schemas and row counts in one go
        try:
            # Create a single query to get all table schemas and row counts
            table_names = [dataset.name for dataset in datasets]
            all_schemas = {}
            row_counts = {}

            for table_name in table_names:
                try:
                    # Get schema
                    columns_info = await self.duckdb.async_query(f"DESCRIBE {table_name}")
                    schema_data = columns_info[['column_name', 'column_type']].to_dict('records')
                    all_schemas[table_name] = schema_data

                    # Get row count
                    row_count_df = await self.duckdb.async_query(f"SELECT COUNT(*) as count FROM {table_name}")
                    row_count = row_count_df["count"].iloc[0]
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
                        # Use smart column matching to preserve descriptions
                        column_mapping = self._smart_match_columns(mongodb_schema_fields, current_schema_fields)

                        # Create updated schema with preserved descriptions using smart matching
                        updated_schema_fields = []
                        for current_field in current_schema_fields:
                            # Try to find matching old column using smart mapping
                            old_column_name = column_mapping.get(current_field.column_name)

                            if old_column_name:
                                # Find the old field to get description
                                existing_field = next(
                                    (f for f in mongodb_schema_fields if f.column_name == old_column_name),
                                    None
                                )
                                desc = existing_field.desc if existing_field else None
                            else:
                                # No match found, try direct name match as fallback
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
                        logger.info(f"Updated schema for dataset: {dataset.name} (preserved descriptions using smart matching)")
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
                    row_count_df = await self.duckdb.async_query(f"SELECT COUNT(*) as count FROM {dataset.name}")
                    row_count = row_count_df["count"].iloc[0]
                    dataset_with_count = await self._add_row_count_to_dataset(dataset, row_count)
                    available_datasets.append(dataset_with_count)
                except Exception:
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

    async def _sync_affected_datasets_after_query(self, user_id: str, table_names: List[str]):
        """Sync schemas for datasets affected by a SQL query"""
        try:
            for table_name in table_names:
                # Remove quotes if present
                table_name = table_name.strip("'\"")

                if not table_name:
                    continue

                # Get dataset from MongoDB
                dataset = await self.crud.get_by_name(table_name, user_id)
                if not dataset:
                    continue

                # Verify table exists in DuckDB before syncing
                try:
                    result = await self.duckdb.async_execute("SHOW TABLES")
                    duckdb_tables = set(row[0] for row in result.fetchall())
                    if table_name not in duckdb_tables:
                        logger.warning(f"Table {table_name} not found in DuckDB, skipping sync")
                        continue
                except Exception as e:
                    logger.warning(f"Error checking table existence for {table_name}: {str(e)}")
                    continue

                # Sync this specific dataset
                try:
                    await self.sync_dataset_schema(user_id, table_name)
                except Exception as sync_error:
                    logger.warning(f"Error syncing dataset {table_name}: {str(sync_error)}")
                    # Continue with other tables even if one fails
                    continue

        except Exception as e:
            logger.error(f"Error syncing affected datasets after query: {str(e)}")
            # Don't raise, just log - we don't want to fail the query if sync fails

    async def sync_dataset_schema(self, user_id: str, dataset_name: str):
        """Manually sync a specific dataset schema with smart column matching"""
        try:
            # Get dataset from MongoDB
            dataset = await self.crud.get_by_name(dataset_name, user_id)
            if not dataset:
                logger.warning(f"Dataset {dataset_name} not found in MongoDB")
                return None

            # Get current schema from DuckDB
            current_columns_info = await self.duckdb.async_query(f"DESCRIBE {dataset_name}")
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
                # Use smart column matching to preserve descriptions
                column_mapping = self._smart_match_columns(mongodb_schema_fields, current_schema_fields)

                # Create updated schema with preserved descriptions using smart matching
                updated_schema_fields = []
                for current_field in current_schema_fields:
                    # Try to find matching old column using smart mapping
                    old_column_name = column_mapping.get(current_field.column_name)

                    if old_column_name:
                        # Find the old field to get description
                        existing_field = next(
                            (f for f in mongodb_schema_fields if f.column_name == old_column_name),
                            None
                        )
                        desc = existing_field.desc if existing_field else None
                    else:
                        # No match found, try direct name match as fallback
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
                logger.info(f"Synced schema for dataset: {dataset_name} (preserved descriptions using smart matching)")
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

      result = await self.duckdb.async_execute("SHOW TABLES")
      duckdb_tables = set(row[0] for row in result.fetchall())
      if dataset.name not in duckdb_tables:
        await self.crud.delete(dataset)
        raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)
      return dataset

    async def delete_dataset(self, user_id: str, dataset_id: str):
      dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
      if not dataset:
        raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

      try:
          await self.duckdb.async_execute(f"DROP TABLE {dataset.name}")
          logger.info(f"Deleted dataset: {dataset.name} for user {user_id}")
      except Exception as e:
        logger.error(f"Error when deleting dataset for user {user_id}: {str(e)}")
        raise AppError(f"Error when deleting dataset: {str(e)}", status_code=HTTP_400_BAD_REQUEST)

      await self.crud.delete(dataset)
      return dataset


    async def get_dataset_data(self, user_id: str, dataset_id: str, skip: int = 0, limit: int = 100):
      dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
      if not dataset:
        raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

      try:
          data = await self.duckdb.async_query(f"SELECT * FROM {dataset.name} LIMIT {limit} OFFSET {skip}")
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

    async def query_dataset(self, user_id: str, query: str, limit: int = 1000):
        """Execute SQL query on dataset with validation and preprocessing"""

        try:
            # Validate SQL syntax
            if not check_sql_syntax(query):
                raise AppError("Invalid SQL syntax", status_code=HTTP_400_BAD_REQUEST)

            # Check if query modifies schema
            is_schema_modifying = is_schema_modifying_query(query)

            # Extract table names from query
            table_names = extract_table_names_from_query(query)

            # Execute query
            if is_schema_modifying:
                # For schema-modifying queries, execute directly without limit
                processed_query = query
                result = await self.duckdb.async_execute(processed_query)
                data_result = result
            else:

                processed_query = add_limit_sql(query, limit)
                data_result = await self.duckdb.async_query(processed_query)

            # If schema was modified, sync affected datasets
            if is_schema_modifying and table_names:
                try:
                    await self._sync_affected_datasets_after_query(user_id, table_names)
                    logger.info(f"Synced schemas for affected tables: {table_names}")
                except Exception as sync_error:
                    logger.warning(f"Failed to sync schemas after query: {str(sync_error)}")
                    # Don't fail the query if sync fails, just log warning

            # Return results
            if is_schema_modifying:
                return {
                    "message": "Schema modified successfully",
                    "affected_tables": table_names
                }
            else:
                return data_result.to_dict('records') if data_result is not None and not data_result.empty else []

        except AppError:
            raise
        except DuckDBLockError as e:
            # Handle DuckDB lock conflicts with a more user-friendly message
            logger.error(f"DuckDB lock conflict when querying dataset for user {user_id}: {str(e)}")
            raise AppError(
                "Database is currently busy processing another query. Please try again in a moment.",
                status_code=HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error when querying dataset for user {user_id}: {str(e)}")
            # Remove "Catalog Error:" prefix from error message
            error_message = str(e)
            if error_message.startswith("Catalog Error:"):
                error_message = error_message.replace("Catalog Error:", "").strip()
            raise AppError(f"Error when querying dataset: {error_message}", status_code=HTTP_400_BAD_REQUEST)

    async def update_dataset(self, user_id: str, dataset_id: str, update_data: DatasetUpdate):
      dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
      if not dataset:
        raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

      # Only update name and description, no schema changes
      update_dict = update_data.model_dump(exclude_unset=True)
      if not update_dict:
        return dataset

      # If name is being updated, rename the table in DuckDB
      if 'name' in update_dict and update_dict['name'] != dataset.name:
        await self.duckdb.async_execute(f"ALTER TABLE {dataset.name} RENAME TO {update_dict['name']}")

      updated_dataset = await self.crud.update(dataset, update_dict)

      # Get row count and add it to the response (similar to get_list_dataset)
      try:
        # Use the updated name if it was changed, otherwise use original name
        table_name = update_dict.get('name', dataset.name)
        row_count_df = await self.duckdb.async_query(f"SELECT COUNT(*) as count FROM {table_name}")
        row_count = row_count_df["count"].iloc[0]
        updated_dataset_with_count = await self._add_row_count_to_dataset(updated_dataset, row_count)
        return updated_dataset_with_count
      except Exception as e:
        logger.error(f"Error getting row count for dataset {dataset_id}: {str(e)}")
        # Return dataset without row_count if there's an error
        return updated_dataset

    async def update_dataset_schema(self, user_id: str, dataset_id: str, descriptions: Dict[str, str]):
        """Update dataset schema descriptions in MongoDB only"""
        dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
        if not dataset:
            raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

        try:
            # Get current schema
            current_schema = dataset.data_schema

            # Update descriptions for matching columns
            updated_schema = []
            for field in current_schema:
                column_name = field['column_name']
                if column_name in descriptions:
                    # Update description
                    field['desc'] = descriptions[column_name]
                updated_schema.append(DataSchemaField(**field))

            # Update schema in MongoDB
            updated_dataset = await self.crud.update_schema(dataset.id, updated_schema)
            logger.info(f"Updated schema descriptions for dataset: {dataset.name}")
            return updated_dataset

        except Exception as e:
            logger.error(f"Error updating schema for dataset {dataset.name}: {str(e)}")
            raise AppError(f"Error updating schema: {str(e)}", status_code=HTTP_400_BAD_REQUEST)

    async def insert_data_from_file(self, user_id: str, dataset_id: str, file_id: str):
        """Insert data from file into existing dataset with automatic column mapping"""
        try:
            # Get dataset
            dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
            if not dataset:
                raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

            # Get file
            file = await self.file_crud.get_by_id(file_id)
            if not file:
                raise AppError("File not found", status_code=HTTP_404_NOT_FOUND)

            # Validate file type
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

            # Get dataset schema
            dataset_columns = [field['column_name'] for field in dataset.data_schema]

            # Get file columns
            file_columns = await self._get_file_columns(user_id, file.file_path, file.file_type)

            # Auto-generate column mapping based on column name matching
            column_mapping = self._generate_automatic_column_mapping(file_columns, dataset_columns)

            # Validate all required dataset columns are mapped
            missing_columns = [col for col in dataset_columns if col not in column_mapping.values()]
            if missing_columns:
                raise AppError(f"Cannot automatically map dataset columns: {', '.join(missing_columns)}. Available file columns: {', '.join(file_columns)}", status_code=HTTP_400_BAD_REQUEST)

            # Insert data with automatic column mapping
            result = await self._insert_data_with_mapping(
                user_id,
                dataset.name,
                file.file_path,
                file.file_type,
                column_mapping
            )

            return {
                "dataset_id": dataset_id,
                "file_id": file_id,
                "rows_inserted": result.get("rows_inserted", 0),
                "column_mapping": column_mapping,
                "auto_mapped": True
            }

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error inserting data from file for user {user_id}: {str(e)}")
            raise AppError(f"Error inserting data from file: {str(e)}", status_code=HTTP_400_BAD_REQUEST)

    def _generate_automatic_column_mapping(self, file_columns: list, dataset_columns: list) -> dict:
        """Generate automatic column mapping based on exact name matching"""
        column_mapping = {}

        # Create mapping for exact matches (case-insensitive)
        dataset_columns_lower = [col.lower() for col in dataset_columns]

        for file_col in file_columns:
            file_col_lower = file_col.lower()
            if file_col_lower in dataset_columns_lower:
                # Find the corresponding dataset column (case-sensitive)
                dataset_col_index = dataset_columns_lower.index(file_col_lower)
                dataset_col = dataset_columns[dataset_col_index]
                column_mapping[file_col] = dataset_col

        return column_mapping


    async def _get_file_columns(self, user_id: str, file_path: str, file_type: str) -> list:
        """Get column names from file"""
        try:
            # Add S3 prefix to file path
            s3_path = f"s3://{user_id}/{file_path}"

            if file_type in ["text/csv", "application/csv", "text/plain"]:
                # Read CSV file to get columns with ignore_errors=true
                df = await self.duckdb.async_query(f"SELECT * FROM read_csv_auto('{s3_path}', header=true, ignore_errors=true) LIMIT 0")
                return df.columns.tolist()
            elif file_type in [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
                "application/vnd.ms-excel.sheet.macroEnabled.12",
                "application/vnd.ms-excel.template.macroEnabled.12",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.template"
            ]:
                # Read Excel file to get columns
                df = await self.duckdb.async_query(f"SELECT * FROM read_excel('{s3_path}', header=true) LIMIT 0")
                return df.columns.tolist()
            else:
                raise AppError("Unsupported file type", status_code=HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error reading file columns: {str(e)}")
            raise AppError(f"Error reading file: {str(e)}", status_code=HTTP_400_BAD_REQUEST)

    async def _insert_data_with_mapping(self, user_id: str, dataset_name: str, file_path: str, file_type: str, column_mapping: dict):
        """Insert data from file with column mapping"""
        try:
            # Add S3 prefix to file path
            s3_path = f"s3://{user_id}/{file_path}"

            # Create temporary table for file data
            temp_table = f"temp_file_data_{dataset_name}"

            if file_type in ["text/csv", "application/csv", "text/plain"]:
                # Read CSV file with ignore_errors=true to handle malformed rows
                await self.duckdb.async_execute(f"CREATE TEMP TABLE {temp_table} AS SELECT * FROM read_csv_auto('{s3_path}', header=true, ignore_errors=true)")
            else:
                # Read Excel file
                await self.duckdb.async_execute(f"CREATE TEMP TABLE {temp_table} AS SELECT * FROM read_excel('{s3_path}', header=true)")

            # Get count of rows to insert
            result = await self.duckdb.async_execute(f"SELECT COUNT(*) FROM {temp_table}")
            row_count = result.fetchone()[0]

            # Build INSERT query with column mapping
            dataset_columns = list(column_mapping.values())

            # Create column selection with mapping
            column_selection = []
            for file_col, dataset_col in column_mapping.items():
                column_selection.append(f"{file_col} AS {dataset_col}")

            # Insert data with mapping
            insert_query = f"""
                INSERT INTO {dataset_name} ({', '.join(dataset_columns)})
                SELECT {', '.join(column_selection)}
                FROM {temp_table}
            """

            await self.duckdb.async_execute(insert_query)

            # Clean up temporary table
            await self.duckdb.async_execute(f"DROP TABLE {temp_table}")

            return {"rows_inserted": row_count}

        except Exception as e:
            logger.error(f"Error inserting data with mapping: {str(e)}")
            raise AppError(f"Error inserting data: {str(e)}", status_code=HTTP_400_BAD_REQUEST)

    async def get_file_and_dataset_columns(self, user_id: str, dataset_id: str, file_id: str):
        """Get file columns and dataset columns for mapping preparation"""
        try:
            # Get dataset
            dataset = await self.crud.get_by_owner_and_id(user_id, dataset_id)
            if not dataset:
                raise AppError("Dataset not found", status_code=HTTP_404_NOT_FOUND)

            # Get file
            file = await self.file_crud.get_by_id(file_id)
            if not file:
                raise AppError("File not found", status_code=HTTP_404_NOT_FOUND)

            # Validate file type
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

            # Get file columns
            file_columns = await self._get_file_columns(user_id, file.file_path, file.file_type)

            # Get dataset columns with schema info
            dataset_columns = []
            for field in dataset.data_schema:
                dataset_columns.append({
                    "column_name": field['column_name'],
                    "column_type": field['column_type'],
                    "description": field.get('desc', '')
                })

            return {
                "file_columns": file_columns,
                "dataset_columns": dataset_columns,
                "file_info": {
                    "file_id": file_id,
                    "file_name": file.file_name,
                    "file_type": file.file_type
                },
                "dataset_info": {
                    "dataset_id": dataset_id,
                    "dataset_name": dataset.name,
                    "description": dataset.description
                }
            }

        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error getting file and dataset columns for user {user_id}: {str(e)}")
            raise AppError(f"Error getting columns: {str(e)}", status_code=HTTP_400_BAD_REQUEST)


