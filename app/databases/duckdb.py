import asyncio
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

    async def _exec_with_retry(self, func, operation_name: str):
        """
        Execute a function with retry logic for DuckDB lock conflicts.

        Args:
            func: Function to execute (must be thread-safe/lock-aware)
            operation_name: Name of operation for logging (e.g., 'query', 'execute')
        """
        await self._ensure_instance()
        self._instance.update_last_used()  # Reset TTL

        # Helper to run the function within the instance lock
        def _execute_locked():
            with self._instance.lock:
                return func()

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                # Run potentially blocking DB operation in a separate thread
                return await asyncio.to_thread(_execute_locked)
            except Exception as e:
                error_str = str(e).lower()
                # Check known lock conflict signatures
                if any(x in error_str for x in ["lock", "conflicting", "concurrency"]):
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                        logger.warning(
                            f"Lock conflict on {operation_name} attempt {attempt + 1}/{MAX_RETRIES} for user {self.user_id}, "
                            f"retrying in {delay}s... Error: {str(e)[:200]}"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        error_msg = (
                            f"Failed to {operation_name} after {MAX_RETRIES} attempts due to DuckDB lock conflict. "
                            f"Original error: {str(e)}"
                        )
                        logger.error(f"{error_msg} (User: {self.user_id})")
                        raise DuckDBLockError(error_msg) from e
                else:
                    raise

        if last_error:
            raise DuckDBLockError(f"Failed to {operation_name} after retries. Error: {last_error}") from last_error
        raise RuntimeError(f"Unexpected error in {operation_name}")


    async def async_query(self, sql: str):
        """Execute query asynchronously with retry mechanism"""
        logger.info(f"Executing SQL query for user {self.user_id}: {sql}")

        def _run_query():
            return self._con.execute(sql).df()

        return await self._exec_with_retry(_run_query, "query")


    async def async_execute(self, sql: str):
        """Execute SQL command asynchronously with retry mechanism"""
        logger.debug(f"Executing SQL command for user {self.user_id}: {sql}")

        def _run_cmd():
            return self._con.execute(sql)

        return await self._exec_with_retry(_run_cmd, "execute")

    def close(self):
        """
        Do not close connection because it is managed by instance manager.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

