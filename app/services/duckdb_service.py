import pandas as pd
import io
import chardet
from typing import Optional, List
from app.utils import get_logger
from app.databases.duckdb import DuckDB

logger = get_logger(__name__)


class DuckDBService:
    """Service for handling file conversions using DuckDB"""

    @staticmethod
    def get_connection(access_key: str, secret_key: str):
        """Get DuckDB connection with MinIO configuration"""
        return DuckDB(access_key=access_key, secret_key=secret_key)

    @staticmethod
    async def convert_to_parquet(file_content: bytes, file_ext: str) -> Optional[bytes]:
        """
        Convert CSV/Excel file to Parquet format using pandas

        Args:
            file_content: File content as bytes
            file_ext: File extension (.csv, .xlsx, .xls)

        Returns:
            Parquet file content as bytes or None if error
        """
        try:
            logger.info(f"Converting file with extension {file_ext} to Parquet")

            # Read file content into DataFrame
            file_buffer = io.BytesIO(file_content)

            if file_ext.lower() == ".csv":
                # Detect encoding before reading CSV
                file_buffer.seek(0)
                raw_data = file_buffer.read()
                detected_encoding = chardet.detect(raw_data)['encoding']

                # Fallback to utf-8 if detection fails
                encoding = detected_encoding if detected_encoding else 'utf-8'
                logger.info(f"Detected encoding: {encoding}")

                # Reset buffer and read CSV with detected encoding
                file_buffer = io.BytesIO(raw_data)
                try:
                    df = pd.read_csv(file_buffer, encoding=encoding)
                except UnicodeDecodeError:
                    # Try with other common encodings
                    logger.warning(f"Failed to read with {encoding}, trying alternative encodings")
                    for alt_encoding in ['utf-16', 'latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            file_buffer = io.BytesIO(raw_data)
                            df = pd.read_csv(file_buffer, encoding=alt_encoding)
                            logger.info(f"Successfully read CSV with encoding: {alt_encoding}")
                            break
                        except (UnicodeDecodeError, UnicodeError):
                            continue
                    else:
                        # If all encodings fail, try with errors='ignore'
                        file_buffer = io.BytesIO(raw_data)
                        df = pd.read_csv(file_buffer, encoding='utf-8', errors='ignore')
                        logger.warning("Read CSV with UTF-8 and ignored errors")
            elif file_ext.lower() in [".xlsx", ".xls"]:
                # Read Excel
                df = pd.read_excel(file_buffer, engine='openpyxl' if file_ext.lower() == ".xlsx" else 'xlrd')
            else:
                logger.error(f"Unsupported file extension for conversion: {file_ext}")
                return None

            # Convert to Parquet
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
            parquet_content = parquet_buffer.getvalue()

            logger.info(f"Successfully converted file to Parquet. Original size: {len(file_content)} bytes, Parquet size: {len(parquet_content)} bytes")
            return parquet_content

        except Exception as e:
            logger.error(f"Failed to convert file to Parquet: {str(e)}")
            return None

    @staticmethod
    async def convert_csv_to_parquet(
        source_s3_path: str,
        parquet_s3_path: str,
        access_key: str,
        secret_key: str
    ) -> bool:
        """
        Convert CSV to Parquet for dataset system

        Args:
            source_s3_path: Full S3 path to source CSV (s3://bucket/raw/file.csv)
            parquet_s3_path: Full S3 path to target Parquet (s3://bucket/data/folder/data.parquet)
            access_key: MinIO access key
            secret_key: MinIO secret key

        Returns:
            True if conversion successful, False otherwise
        """
        try:
            logger.info(f"Converting CSV to Parquet: {source_s3_path} -> {parquet_s3_path}")

            with DuckDB(access_key=access_key, secret_key=secret_key) as duckdb_conn:
                # Try different encodings for CSV
                encodings_to_try = ['UTF-8', 'UTF-16', 'LATIN-1', 'CP1252', 'ISO-8859-1']

                for encoding in encodings_to_try:
                    try:
                        logger.info(f"Trying to read CSV with encoding: {encoding}")

                        sql_query = f"""
                        COPY (
                            SELECT *
                            FROM read_csv_auto('{source_s3_path}', encoding='{encoding}', ignore_errors=true)
                        ) TO '{parquet_s3_path}' (FORMAT PARQUET);
                        """

                        duckdb_conn.execute(sql_query)
                        logger.info(f"Successfully converted CSV to Parquet with encoding {encoding}")
                        return True

                    except Exception as encoding_error:
                        logger.warning(f"Failed with encoding {encoding}: {str(encoding_error)}")
                        continue

                # Final attempt with ignore_errors and all_varchar
                logger.warning("All encodings failed, trying with ignore_errors=true and all_varchar=true")
                try:
                    sql_query = f"""
                    COPY (
                        SELECT *
                        FROM read_csv_auto('{source_s3_path}', ignore_errors=true, all_varchar=true)
                    ) TO '{parquet_s3_path}' (FORMAT PARQUET);
                    """

                    duckdb_conn.execute(sql_query)
                    logger.info("Successfully converted CSV to Parquet with ignore_errors=true")
                    return True

                except Exception as final_error:
                    logger.error(f"Final attempt failed: {str(final_error)}")
                    return False

        except Exception as e:
            logger.error(f"Failed to convert CSV to Parquet: {str(e)}")
            return False

    @staticmethod
    async def convert_excel_to_parquet(
        user_id: str,
        excel_object_name: str,
        parquet_s3_path: str,
        minio_client
    ) -> bool:
        """
        Convert Excel to Parquet for dataset system

        Args:
            user_id: User ID (bucket name)
            excel_object_name: Excel file object name in MinIO
            parquet_s3_path: Full S3 path to target Parquet
            minio_client: MinIO client for file operations

        Returns:
            True if conversion successful, False otherwise
        """
        try:
            logger.info(f"Converting Excel to Parquet: {excel_object_name} -> {parquet_s3_path}")

            # Download Excel file from MinIO
            excel_object = minio_client.client.get_object(user_id, excel_object_name)
            excel_content = excel_object.read()

            # Convert Excel to Parquet using pandas
            parquet_content = await DuckDBService.convert_to_parquet(excel_content, ".xlsx")

            if parquet_content:
                # Extract parquet object name from S3 path
                parquet_object_name = parquet_s3_path.replace(f"s3://{user_id}/", "")

                # Upload Parquet to MinIO
                upload_success = minio_client.upload_bytes(
                    bucket_name=user_id,
                    object_name=parquet_object_name,
                    data=parquet_content,
                    content_type="application/octet-stream"
                )

                if upload_success:
                    logger.info(f"Successfully converted Excel to Parquet: {parquet_s3_path}")
                    return True
                else:
                    logger.error(f"Failed to upload Parquet file: {parquet_s3_path}")
                    return False
            else:
                logger.error("Failed to convert Excel content to Parquet")
                return False

        except Exception as e:
            logger.error(f"Failed to convert Excel to Parquet: {str(e)}")
            return False

    @staticmethod
    def get_data_from_parquet(
        parquet_s3_path: str,
        start_row: int,
        limit: int,
        access_key: str,
        secret_key: str
    ) -> List[dict]:
        """
        Get data from Parquet file for dataset system

        Args:
            parquet_s3_path: Full S3 path to Parquet file
            start_row: Starting row (offset)
            limit: Number of rows to return
            access_key: MinIO access key
            secret_key: MinIO secret key

        Returns:
            List of dictionaries containing the data
        """
        try:
            with DuckDB(access_key=access_key, secret_key=secret_key) as duckdb_conn:
                sql_query = f"SELECT * FROM read_parquet('{parquet_s3_path}') LIMIT {limit} OFFSET {start_row}"
                df = duckdb_conn.query(sql_query)
                return df.to_dict(orient='records')
        except Exception as e:
            logger.error(f"Failed to get data from parquet: {str(e)}")
            return []

