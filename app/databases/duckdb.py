import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from app.utils import get_logger
from app.databases.duckdb_manager import get_instance_manager
from app.configs.settings import settings

logger = get_logger(__name__)

# Retry configuration for lock conflicts
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 0.1  # 100ms
MAX_RETRY_DELAY = 1.0  # 1 second


class DuckDBLockError(Exception):
    """Custom exception for DuckDB lock conflicts"""
    pass

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
        """Execute query asynchronously and update TTL with retry mechanism for lock conflicts"""
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

        # Retry mechanism for lock conflicts
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return await loop.run_in_executor(executor, _execute_query)
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a lock conflict error
                if "lock" in error_str or "conflicting" in error_str or "concurrency" in error_str:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        # Exponential backoff: 0.1s, 0.2s, 0.4s, etc.
                        delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                        logger.warning(
                            f"Lock conflict on query attempt {attempt + 1}/{MAX_RETRIES} for user {self.user_id}, "
                            f"retrying in {delay}s... Error: {str(e)[:200]}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        error_msg = (
                            f"Failed to execute query after {MAX_RETRIES} attempts due to DuckDB lock conflict. "
                            f"This usually happens when multiple queries try to access the same database file simultaneously. "
                            f"Original error: {str(e)}"
                        )
                        logger.error(f"{error_msg} (User: {self.user_id})")
                        raise DuckDBLockError(error_msg) from e
                else:
                    # Not a lock error, re-raise immediately
                    raise

        # Should not reach here, but handle it
        if last_error:
            raise DuckDBLockError(
                f"Failed to execute query due to lock conflict after {MAX_RETRIES} retries. "
                f"Original error: {str(last_error)}"
            ) from last_error
        raise RuntimeError("Unexpected error in async_query")

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
        """Execute SQL command asynchronously and update TTL with retry mechanism for lock conflicts"""
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

        # Retry mechanism for lock conflicts
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return await loop.run_in_executor(executor, _execute_command)
            except Exception as e:
                error_str = str(e).lower()
                # Check if it's a lock conflict error
                if "lock" in error_str or "conflicting" in error_str or "concurrency" in error_str:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        # Exponential backoff: 0.1s, 0.2s, 0.4s, etc.
                        delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                        logger.warning(
                            f"Lock conflict on execute attempt {attempt + 1}/{MAX_RETRIES} for user {self.user_id}, "
                            f"retrying in {delay}s... Error: {str(e)[:200]}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        error_msg = (
                            f"Failed to execute command after {MAX_RETRIES} attempts due to DuckDB lock conflict. "
                            f"This usually happens when multiple queries try to access the same database file simultaneously. "
                            f"Original error: {str(e)}"
                        )
                        logger.error(f"{error_msg} (User: {self.user_id})")
                        raise DuckDBLockError(error_msg) from e
                else:
                    # Not a lock error, re-raise immediately
                    raise

        # Should not reach here, but handle it
        if last_error:
            raise DuckDBLockError(
                f"Failed to execute command due to lock conflict after {MAX_RETRIES} retries. "
                f"Original error: {str(last_error)}"
            ) from last_error
        raise RuntimeError("Unexpected error in async_execute")

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

