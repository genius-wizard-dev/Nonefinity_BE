import duckdb
import threading
from typing import Dict, Optional
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


class DuckDBConnectionPool:
    """Connection pool for reusing DuckDB connections"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._connections = {}
                    cls._instance._connection_lock = threading.Lock()
        return cls._instance

    def get_connection(self, access_key: str, secret_key: str) -> duckdb.DuckDBPyConnection:
        """Get a connection from the pool, create a new one if it doesn't exist"""
        connection_key = f"{access_key}:{secret_key}"

        with self._connection_lock:
            if connection_key not in self._connections:
                logger.info(f"Create a new duckdb connection for the key: {connection_key[:20]}...")
                conn = duckdb.connect(database=":memory:")
                conn.execute("LOAD httpfs;")

                # Configure S3/MinIO
                endpoint = settings.MINIO_URL.replace("http://", "").replace("https://", "")
                conn.execute(f"SET s3_endpoint='{endpoint}';")
                conn.execute(f"SET s3_access_key_id='{access_key}';")
                conn.execute(f"SET s3_secret_access_key='{secret_key}';")
                ssl_flag = "true" if settings.MINIO_SSL else "false"
                conn.execute(f"SET s3_use_ssl={ssl_flag};")
                conn.execute("SET s3_url_style='path';")

                self._connections[connection_key] = conn
            else:
                logger.debug(f"Reuse duckdb connection for key: {connection_key[:20]}...")

        return self._connections[connection_key]

    def close_connection(self, access_key: str, secret_key: str):
        """Close a specific connection"""
        connection_key = f"{access_key}:{secret_key}"

        with self._connection_lock:
            if connection_key in self._connections:
                self._connections[connection_key].close()
                del self._connections[connection_key]
                logger.info(f"Closed duckdb connection: {connection_key[:20]}...")

    def close_all_connections(self):
        """Close all connections"""
        with self._connection_lock:
            for conn in self._connections.values():
                conn.close()
            self._connections.clear()
            logger.info("Closed all duckdb connections")


# Global connection pool instance
connection_pool = DuckDBConnectionPool()


class DuckDB:
    def __init__(self, access_key: str, secret_key: str, reuse_connection: bool = True):
        self.access_key = access_key
        self.secret_key = secret_key
        self.reuse_connection = reuse_connection

        if reuse_connection:
            # Use connection pool
            self.con = connection_pool.get_connection(access_key, secret_key)
            self._should_close = False
        else:
            # Create a new connection like before
            self.con = duckdb.connect(database=":memory:")
            self.con.execute("LOAD httpfs;")
            endpoint = settings.MINIO_URL.replace("http://", "").replace("https://", "")
            self.con.execute(f"SET s3_endpoint='{endpoint}';")
            self.con.execute(f"SET s3_access_key_id='{access_key}';")
            self.con.execute(f"SET s3_secret_access_key='{secret_key}';")
            ssl_flag = "true" if settings.MINIO_SSL else "false"
            self.con.execute(f"SET s3_use_ssl={ssl_flag};")
            self.con.execute("SET s3_url_style='path';")
            self._should_close = True

    def query(self, sql: str):
        logger.info(f"Executing SQL: {sql}")
        return self.con.execute(sql).df()

    def execute(self, sql: str):
        """Return DuckDB relation for chaining instead of Pandas df"""
        logger.debug(f"Executing raw SQL: {sql}")
        return self.con.execute(sql)

    def close(self):
        """Close the connection if not using pool"""
        if self._should_close:
            self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

