
import duckdb
from app.utils import get_logger
from app.databases.duckdb_manager import get_instance_manager

logger = get_logger(__name__)


def init_duckdb_extensions():
    """
    Install the necessary DuckDB extensions (only need to run once when app starts).
    """
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL httpfs;")
    con.close()

class DuckDB:
    def __init__(self, user_id: str, access_key: str, secret_key: str):
        """
        Use cached DuckDB instance from instance manager.
        Instance will be automatically managed with TTL and cleanup worker.
        """
        self.user_id = user_id
        self.access_key = access_key
        self.secret_key = secret_key

        logger.debug(f"Getting DuckDB instance for user: {user_id}")

        # Get cached instance from manager
        manager = get_instance_manager()
        self.instance = manager.get_instance(user_id, access_key, secret_key)
        self.con = self.instance.con

    def query(self, sql: str):
        """Execute query and update TTL"""
        logger.info(f"Executing SQL query for user {self.user_id}: {sql}")
        self.instance.update_last_used()  # Reset TTL
        return self.con.execute(sql).df()

    def execute(self, sql: str):
        """Execute SQL command and update TTL"""
        logger.debug(f"Executing SQL command for user {self.user_id}: {sql}")
        self.instance.update_last_used()  # Reset TTL
        return self.con.execute(sql)

    def close(self):
        """
        Do not close connection because it is managed by instance manager.
        Instance will be automatically cleaned up after TTL.
        """
        logger.debug(f"DuckDB instance for user {self.user_id} will be automatically cleaned up after TTL")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Do not close connection, only log
        logger.debug(f"Context exit for DuckDB instance user {self.user_id}")

