from app.utils import get_logger
from app.databases.duckdb import DuckDB
from app.crud.dataset import DatasetCRUD
from app.crud.file import FileCRUD
from app.schemas.dataset import DatasetCreate
from app.core.exceptions import AppError
from starlette.status import HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST


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


    async def convert(
      self,
      user_id: str,
      file_id: str,
      dataset_name: str,
      description: str
    ):
      try:

        dataset = await self.crud.get_by_name(dataset_name)
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
      return await self.crud.get_by_owner(user_id, skip, limit)

    async def get_dataset(self, user_id: str, dataset_id: str):
      return await self.crud.get_by_owner_and_id(user_id, dataset_id)

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
