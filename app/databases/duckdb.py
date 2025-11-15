import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from app.utils import get_logger
from app.databases.duckdb_manager import get_instance_manager
from app.configs.settings import settings

logger = get_logger(__name__)

# Thread pool executor for DuckDB operations
_thread_pool: Optional[ThreadPoolExecutor] = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Get or create thread pool executor for DuckDB operations"""
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(
            max_workers=settings.DUCKDB_THREAD_POOL_SIZE,
            thread_name_prefix="duckdb"
        )
    return _thread_pool


class DuckDB:
    def __init__(self, user_id: str, access_key: str, secret_key: str):
        """
        Use cached DuckDB instance from instance manager.
        Instance will be automatically managed with TTL and cleanup worker.
        """
        self.user_id = user_id
        self.access_key = access_key
        self.secret_key = secret_key
        self._instance = None
        self._con = None

    async def _ensure_instance(self):
        """Ensure instance is initialized (async)"""
        if self._instance is None:
            logger.debug(f"Getting DuckDB instance for user: {self.user_id}")
            manager = await get_instance_manager()
            self._instance = await manager.get_instance(self.user_id, self.access_key, self.secret_key)
            self._con = self._instance.con

    def query(self, sql: str):
        """
        Execute query and update TTL (synchronous, deprecated)
        Use async_query() instead for async operations.
        """
        logger.warning("Using synchronous query() method. Consider using async_query() instead.")
        logger.info(f"Executing SQL query for user {self.user_id}: {sql}")
        if self._instance is None:
            raise RuntimeError("Instance not initialized. Use async_query() or await _ensure_instance() first.")
        self._instance.update_last_used()  # Reset TTL
        return self._con.execute(sql).df()

    async def async_query(self, sql: str):
        """Execute query asynchronously and update TTL"""
        await self._ensure_instance()
        logger.info(f"Executing SQL query for user {self.user_id}: {sql}")
        self._instance.update_last_used()  # Reset TTL

        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        executor = get_thread_pool()

        def _execute_query():
            # Use instance lock to ensure thread-safe execution
            with self._instance.lock:
                return self._con.execute(sql).df()

        return await loop.run_in_executor(executor, _execute_query)

    def execute(self, sql: str):
        """
        Execute SQL command and update TTL (synchronous, deprecated)
        Use async_execute() instead for async operations.
        """
        logger.warning("Using synchronous execute() method. Consider using async_execute() instead.")
        logger.debug(f"Executing SQL command for user {self.user_id}: {sql}")
        if self._instance is None:
            raise RuntimeError("Instance not initialized. Use async_execute() or await _ensure_instance() first.")
        self._instance.update_last_used()  # Reset TTL
        return self._con.execute(sql)

    async def async_execute(self, sql: str):
        """Execute SQL command asynchronously and update TTL"""
        await self._ensure_instance()
        logger.debug(f"Executing SQL command for user {self.user_id}: {sql}")
        self._instance.update_last_used()  # Reset TTL

        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        executor = get_thread_pool()

        def _execute_command():
            # Use instance lock to ensure thread-safe execution
            with self._instance.lock:
                return self._con.execute(sql)

        return await loop.run_in_executor(executor, _execute_command)

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

