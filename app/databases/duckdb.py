import duckdb
from app.configs.settings import settings
from app.utils import get_logger

logger = get_logger(__name__)


def init_duckdb_extensions():
    """
    Install the necessary DuckDB extensions (only need to run once when app starts).
    """
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL httpfs;")
    con.close()


class DuckDB:
    def __init__(self, access_key: str, secret_key: str):
        """
        Create a new DuckDB connection for each instance.
        No more connection pooling to avoid RAM issues.
        """
        self.access_key = access_key
        self.secret_key = secret_key

        logger.debug(f"Creating new DuckDB connection for user: {access_key[:10]}...")

        # Always create a new connection
        self.con = duckdb.connect(database=":memory:")
        self.con.execute("LOAD httpfs;")

        # Configure S3/MinIO
        endpoint = settings.MINIO_URL.replace("http://", "").replace("https://", "")
        self.con.execute(f"SET s3_endpoint='{endpoint}';")
        self.con.execute(f"SET s3_access_key_id='{access_key}';")
        self.con.execute(f"SET s3_secret_access_key='{secret_key}';")
        ssl_flag = "true" if settings.MINIO_SSL else "false"
        self.con.execute(f"SET s3_use_ssl={ssl_flag};")
        self.con.execute("SET s3_url_style='path';")

    def query(self, sql: str):
        logger.info(f"Executing SQL: {sql}")
        return self.con.execute(sql).df()

    def execute(self, sql: str):
        """Return DuckDB relation for chaining instead of Pandas df"""
        logger.debug(f"Executing raw SQL: {sql}")
        return self.con.execute(sql)

    def close(self):
        """Always close the connection when done"""
        if hasattr(self, 'con') and self.con:
            self.con.close()
            logger.debug(f"Closed DuckDB connection for user: {self.access_key[:10]}...")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

