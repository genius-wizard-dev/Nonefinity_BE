import duckdb
from app.configs.settings import settings
from app.utils import get_logger

logger = get_logger(__name__)

class DuckDB:
    def __init__(self, access_key: str, secret_key: str):
        self.con = duckdb.connect(database=":memory:")
        self.con.execute("INSTALL httpfs;")
        self.con.execute("LOAD httpfs;")
        self.con.execute(f"SET s3_endpoint='{settings.MINIO_URL}';")
        self.con.execute(f"SET s3_access_key_id='{access_key}';")
        self.con.execute(f"SET s3_secret_access_key='{secret_key}';")
        ssl_flag = "true" if settings.MINIO_SSL else "false"
        self.con.execute(f"SET s3_use_ssl={ssl_flag};")

    def query(self, sql: str):
        logger.info(f"Executing SQL: {sql}")
        return self.con.execute(sql).df()

    def execute(self, sql: str):
        """Return DuckDB relation for chaining instead of Pandas df"""
        logger.debug(f"Executing raw SQL: {sql}")
        return self.con.execute(sql)

    def close(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

