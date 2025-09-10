import pandas as pd
import io
from typing import Optional
from app.utils import get_logger
from app.databases.duckdb import DuckDB

logger = get_logger(__name__)


class DuckDBService:
    """Service for handling file conversions using DuckDB"""

    @staticmethod
    async def convert_to_parquet(file_content: bytes, file_ext: str) -> Optional[bytes]:
        """
        Convert CSV/Excel file to Parquet format using pandas

        Args:
            file_content: Nội dung file dạng bytes
            file_ext: Extension của file (.csv, .xlsx, .xls)

        Returns:
            Parquet file content as bytes hoặc None nếu lỗi
        """
        try:
            logger.info(f"Converting file with extension {file_ext} to Parquet")

            # Đọc file content vào DataFrame
            file_buffer = io.BytesIO(file_content)

            if file_ext.lower() == ".csv":
                # Đọc CSV
                df = pd.read_csv(file_buffer, encoding='utf-8')
            elif file_ext.lower() in [".xlsx", ".xls"]:
                # Đọc Excel
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
    async def convert_csv_to_parquet_with_duckdb(
        user_id: str,
        access_key: str,
        secret_key: str,
        csv_s3_path: str,
        parquet_s3_path: str
    ) -> bool:
        """
        Convert CSV từ MinIO sang Parquet sử dụng DuckDB

        Args:
            user_id: ID của user (dùng làm bucket name)
            access_key: MinIO access key
            secret_key: MinIO secret key
            csv_s3_path: Đường dẫn CSV trong MinIO (ví dụ: raw/abc123.csv)
            parquet_s3_path: Đường dẫn Parquet muốn lưu (ví dụ: process/abc123/001.parquet)

        Returns:
            True nếu convert thành công, False nếu lỗi
        """
        try:
            logger.info(f"Converting CSV to Parquet using DuckDB: {csv_s3_path} -> {parquet_s3_path}")

            # Tạo kết nối DuckDB với MinIO
            with DuckDB(access_key=access_key, secret_key=secret_key) as duckdb_conn:
                # Tạo full S3 path
                csv_full_path = f"s3://{user_id}/{csv_s3_path}"
                parquet_full_path = f"s3://{user_id}/{parquet_s3_path}"

                # Đọc CSV và ghi ra Parquet
                sql_query = f"""
                COPY (
                    SELECT *
                    FROM read_csv_auto('{csv_full_path}')
                ) TO '{parquet_full_path}' (FORMAT PARQUET);
                """

                duckdb_conn.execute(sql_query)

                logger.info(f"Successfully converted CSV to Parquet: {parquet_full_path}")
                return True

        except Exception as e:
            logger.error(f"Failed to convert CSV to Parquet with DuckDB: {str(e)}")
            return False

    @staticmethod
    async def convert_excel_to_parquet_with_duckdb(
        user_id: str,
        excel_s3_path: str,
        parquet_s3_path: str,
        minio_client
    ) -> bool:
        """
        Convert Excel từ MinIO sang Parquet (Excel cần download về trước vì DuckDB không đọc trực tiếp)

        Args:
            user_id: ID của user (bucket name)
            excel_s3_path: Đường dẫn Excel trong MinIO
            parquet_s3_path: Đường dẫn Parquet muốn lưu
            minio_client: MinIO client để download file

        Returns:
            True nếu convert thành công, False nếu lỗi
        """
        try:
            logger.info(f"Converting Excel to Parquet: {excel_s3_path} -> {parquet_s3_path}")

            # Download Excel file từ MinIO
            excel_object = minio_client.client.get_object(user_id, excel_s3_path)
            excel_content = excel_object.read()

            # Convert Excel to Parquet using pandas
            parquet_content = await DuckDBService.convert_to_parquet(excel_content, ".xlsx")

            if parquet_content:
                # Upload Parquet back to MinIO
                upload_success = minio_client.upload_bytes(
                    bucket_name=user_id,
                    object_name=parquet_s3_path,
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
                logger.error(f"Failed to convert Excel content to Parquet")
                return False

        except Exception as e:
            logger.error(f"Failed to convert Excel to Parquet: {str(e)}")
            return False

    @staticmethod
    def get_parquet_object_name(original_object_name: str, unique_filename: str, version: int = 1) -> str:
        """
        Tạo object name cho file Parquet trong thư mục process/

        Args:
            original_object_name: Tên object gốc (ví dụ: raw/abc123.csv)
            unique_filename: Chuỗi unique 6 ký tự (ví dụ: "abc123")
            version: Số version (mặc định là 1)

        Returns:
            Object name cho Parquet (ví dụ: process/abc123/001.parquet)
        """
        # Format version number với 3 chữ số (001, 002, 003...)
        version_str = f"{version:03d}"

        return f"process/{unique_filename}/{version_str}.parquet"

    @staticmethod
    def get_version_parquet_path(unique_filename: str, version: int) -> str:
        """
        Tạo path cho Parquet version khi chỉnh sửa

        Args:
            unique_filename: Chuỗi unique 6 ký tự (ví dụ: b161b6)
            version: Số version

        Returns:
            Path cho Parquet version (ví dụ: process/b161b6/003.parquet)
        """
        version_str = f"{version:03d}"
        return f"process/{unique_filename}/{version_str}.parquet"
