import time
import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List
from collections import deque
import duckdb
from app.configs.settings import settings
from app.utils import get_logger

logger = get_logger(__name__)

# Thread pool for blocking DuckDB initialization
_init_thread_pool: Optional[ThreadPoolExecutor] = None


def get_init_thread_pool() -> ThreadPoolExecutor:
    """Get or create thread pool for DuckDB initialization"""
    global _init_thread_pool
    if _init_thread_pool is None:
        _init_thread_pool = ThreadPoolExecutor(
            max_workers=4,  # Allow parallel initialization for different users
            thread_name_prefix="duckdb_init"
        )
    return _init_thread_pool


class DuckDBInstance:
    """Wrapper for DuckDB connection with TTL tracking"""
    def __init__(self, user_id: str, access_key: str, secret_key: str):
        self.user_id = user_id
        self.access_key = access_key
        self.secret_key = secret_key
        self.last_used = time.time()
        self.use_count = 0  # Track usage for connection pooling
        self.lock = threading.Lock()  # Lock for thread-safe query execution
        temp_folder = settings.DUCKDB_TEMP_FOLDER
        self.db_path = os.path.join(temp_folder, f"{user_id}.nonefinity")

        # Create directory if it doesn't exist to store database files
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize DuckDB connection with S3/MinIO configuration
        self._initialize_connection()

    def _initialize_connection(self):
      """Initialize DuckDB connection with S3/MinIO settings"""
      try:
          logger.info("Initializing DuckDB instance for user: %s", self.user_id)

          # --- Connect DuckDB ---
          self.con = duckdb.connect(database=self.db_path)

          # --- Install & load extensions ---
          extensions = ["aws", "httpfs", "parquet", "ducklake", "postgres", "excel"]
          for ext in extensions:
              self.con.execute(f"INSTALL {ext};")
              self.con.execute(f"LOAD {ext};")

          # --- S3 secret cho từng user ---
          endpoint = settings.MINIO_URL.replace("http://", "").replace("https://", "")
          ssl_flag = "true" if settings.MINIO_SSL else "false"
          self.con.execute(f"""
              CREATE OR REPLACE SECRET (
                  TYPE s3,
                  PROVIDER config,
                  KEY_ID '{self.access_key}',
                  SECRET '{self.secret_key}',
                  ENDPOINT '{endpoint}',
                  USE_SSL {ssl_flag},
                  URL_STYLE path
              );
          """)

          # --- Postgres secret dùng chung ---
          self.con.execute(f"""
              CREATE OR REPLACE SECRET(
                  TYPE postgres,
                  HOST '{settings.POSTGRES_HOST}',
                  PORT {settings.POSTGRES_PORT},
                  DATABASE '{settings.POSTGRES_DB}',
                  USER '{settings.POSTGRES_USER}',
                  PASSWORD '{settings.POSTGRES_PASSWORD}'
              );
          """)

          # --- Attach DuckLake catalog riêng cho user ---
          self.catalog_name = f"catalog_{self.user_id}"
          self.data_path = f"s3://{self.user_id}/data/"

          # Detach catalog nếu đã tồn tại trước đó
          try:
              self.con.execute(f'DETACH CATALOG "{self.catalog_name}";')
              logger.debug(f"Detached existing catalog: {self.catalog_name}")
          except Exception:
              pass

          self.con.execute(f"""
              ATTACH 'ducklake:postgres:' AS "{self.catalog_name}" (
                DATA_PATH '{self.data_path}'
              );
          """)
          self.con.execute(f"""
                           USE '{self.catalog_name}';
          """)

          logger.info("DuckDB instance initialized successfully for user: %s", self.user_id)

      except Exception as e:
          logger.error("Error initializing DuckDB instance for user %s: %s", self.user_id, str(e))
          raise


    def update_last_used(self):
        """Update last used time to reset TTL"""
        self.last_used = time.time()
        logger.debug(f"TTL reset for user {self.user_id}")

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if instance has expired"""
        return time.time() - self.last_used > ttl_seconds

    def close(self):
        """Close connection and delete database file"""
        try:
            if hasattr(self, 'con') and self.con:
                # Detach catalog trước khi đóng connection
                try:
                    if hasattr(self, 'catalog_name'):
                        self.con.execute(f'DETACH "{self.catalog_name}";')
                        logger.debug(f"Detached catalog {self.catalog_name} before closing")
                except Exception:
                    # Bỏ qua lỗi detach
                    pass

                self.con.close()
                logger.debug(f"Closed DuckDB connection for user: {self.user_id}")

            # Delete database file
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info(f"Deleted database file for user: {self.user_id}")

        except Exception as e:
            logger.error(f"Error closing instance for user {self.user_id}: {str(e)}")


class DuckDBInstanceManager:
    """Manage cache DuckDB instances with TTL, connection pooling, and auto cleanup"""

    def __init__(self, instance_ttl: int = 600, cleanup_interval: int = 300, pool_size: int = 3):
        # Connection pools per user: Dict[user_id, List[DuckDBInstance]]
        self.connection_pools: Dict[str, deque] = {}
        # All instances for cleanup tracking
        self.all_instances: Dict[str, List[DuckDBInstance]] = {}
        # Track ongoing initialization per user to avoid duplicate init
        self._pending_init: Dict[str, asyncio.Event] = {}
        self.lock = asyncio.Lock()
        self.instance_ttl = instance_ttl  # 10 minutes
        self.cleanup_interval = cleanup_interval  # 5 minutes
        self.pool_size = pool_size  # Number of connections per user
        self._cleanup_task = None
        self._stop_cleanup = False

        logger.info(f"DuckDBInstanceManager initialized with TTL: {instance_ttl}s, cleanup interval: {cleanup_interval}s, pool size: {pool_size}")

    async def get_instance(self, user_id: str, access_key: str, secret_key: str) -> DuckDBInstance:
        """
        Get or create DuckDB instance from connection pool for user.
        IMPORTANT: DuckDB only allows ONE connection per database file.
        Therefore, we ensure only ONE instance per user_id to avoid lock conflicts.

        This method is now non-blocking - initialization runs in a thread pool
        to prevent blocking other async operations.

        If multiple requests for the same user come in simultaneously, only the
        first one creates the instance while others wait for it to complete.

        Args:
            user_id: ID of user
            access_key: MinIO access key
            secret_key: MinIO secret key

        Returns:
            DuckDBInstance: Single instance for user (reused if exists and not expired)
        """
        while True:
            # Check if instance already exists or if initialization is pending
            async with self.lock:
                # Initialize pool for user if not exists
                if user_id not in self.connection_pools:
                    self.connection_pools[user_id] = deque()
                    self.all_instances[user_id] = []

                pool = self.connection_pools[user_id]
                all_instances = self.all_instances[user_id]

                # DuckDB only allows ONE connection per database file
                # So we only keep ONE instance per user_id
                if pool:
                    instance = pool[0]  # Get the single instance (don't remove it)

                    # Check if instance has expired
                    if instance.is_expired(self.instance_ttl):
                        logger.debug(f"Instance expired for user: {user_id}, closing and creating new one")
                        try:
                            instance.close()
                        except Exception as e:
                            logger.error(f"Error closing expired instance: {e}")
                        all_instances.clear()
                        pool.clear()
                    else:
                        # Instance is valid, use it
                        instance.update_last_used()
                        instance.use_count += 1
                        logger.debug(f"Reusing existing instance for user: {user_id}")
                        return instance

                # Check if another task is already initializing for this user
                if user_id in self._pending_init:
                    logger.debug(f"Waiting for ongoing initialization for user: {user_id}")
                    pending_event = self._pending_init[user_id]
                    # Release lock and wait for the other task to finish
                else:
                    # We are the first to initialize - create pending event
                    self._pending_init[user_id] = asyncio.Event()
                    pending_event = None
                    break  # Exit the while loop to create instance

            # Wait for the other task to complete initialization
            if pending_event:
                await pending_event.wait()
                # Loop back to get the newly created instance
                continue

        # No valid instance exists, create new one OUTSIDE the lock
        # This prevents blocking other users while one user's instance is being initialized
        logger.info(f"Creating new DuckDB instance for user: {user_id}")

        try:
            # Run blocking initialization in thread pool to not block event loop
            loop = asyncio.get_event_loop()
            executor = get_init_thread_pool()

            def _create_instance():
                """Create DuckDBInstance in thread pool"""
                return DuckDBInstance(user_id, access_key, secret_key)

            instance = await loop.run_in_executor(executor, _create_instance)

            # Now acquire lock to add to pool
            async with self.lock:
                # Clear any old instances
                if user_id in self.connection_pools:
                    self.connection_pools[user_id].clear()
                if user_id in self.all_instances:
                    self.all_instances[user_id].clear()

                # Re-initialize pool if needed (could have been deleted during long init)
                if user_id not in self.connection_pools:
                    self.connection_pools[user_id] = deque()
                if user_id not in self.all_instances:
                    self.all_instances[user_id] = []

                instance.update_last_used()
                instance.use_count = 1
                self.all_instances[user_id].append(instance)
                self.connection_pools[user_id].append(instance)
                return instance
        finally:
            # Always signal completion and clean up pending event
            async with self.lock:
                if user_id in self._pending_init:
                    self._pending_init[user_id].set()  # Signal waiting tasks
                    del self._pending_init[user_id]

    async def _cleanup_instance(self, user_id: str):
        """Cleanup a specific instance (called with lock)"""
        if user_id in self.all_instances:
            try:
                instances_to_remove = []
                for instance in self.all_instances[user_id]:
                    if instance.is_expired(self.instance_ttl):
                        instances_to_remove.append(instance)

                for instance in instances_to_remove:
                    try:
                        instance.close()
                        self.all_instances[user_id].remove(instance)
                        if user_id in self.connection_pools:
                            try:
                                self.connection_pools[user_id].remove(instance)
                            except ValueError:
                                pass  # Already removed
                    except Exception as e:
                        logger.error(f"Error closing instance: {e}")

                # Clean up empty pools
                if user_id in self.connection_pools and not self.connection_pools[user_id]:
                    del self.connection_pools[user_id]
                if user_id in self.all_instances and not self.all_instances[user_id]:
                    del self.all_instances[user_id]
                    logger.info(f"Cleaned up all instances for user: {user_id}")
            except Exception as e:
                logger.error(f"Error cleaning up instances for user {user_id}: {str(e)}")

    async def cleanup_expired_instances(self):
        """Cleanup all expired instances"""
        expired_count = 0

        async with self.lock:
            user_ids = list(self.all_instances.keys())
            for user_id in user_ids:
                if user_id in self.all_instances:
                    instances_to_remove = []
                    for instance in self.all_instances[user_id]:
                        if instance.is_expired(self.instance_ttl):
                            instances_to_remove.append(instance)

                    for instance in instances_to_remove:
                        try:
                            instance.close()
                            self.all_instances[user_id].remove(instance)
                            if user_id in self.connection_pools:
                                try:
                                    self.connection_pools[user_id].remove(instance)
                                except ValueError:
                                    pass
                            expired_count += 1
                        except Exception as e:
                            logger.error(f"Error closing expired instance: {e}")

                    # Clean up empty pools
                    if user_id in self.connection_pools and not self.connection_pools[user_id]:
                        del self.connection_pools[user_id]
                    if user_id in self.all_instances and not self.all_instances[user_id]:
                        del self.all_instances[user_id]

        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired instances")

    def start_cleanup_worker(self):
        """Start background async task to cleanup expired instances"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._stop_cleanup = False
            self._cleanup_task = asyncio.create_task(self._cleanup_worker())
            logger.info("Background cleanup worker started")

    def stop_cleanup_worker(self):
        """Stop background cleanup worker"""
        self._stop_cleanup = True
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("Background cleanup worker stopped")

    async def _cleanup_worker(self):
        """Background async worker to cleanup expired instances"""
        logger.info("Background cleanup worker started")

        while not self._stop_cleanup:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if not self._stop_cleanup:
                    await self.cleanup_expired_instances()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup worker: {str(e)}")

    async def cleanup_all(self):
        """Cleanup all instances (used when shutting down app)"""
        async with self.lock:
            user_ids = list(self.all_instances.keys())
            for user_id in user_ids:
                await self._cleanup_instance(user_id)

        logger.info("Cleaned up all DuckDB instances")

    async def get_stats(self) -> dict:
        """Get statistics about current instances"""
        async with self.lock:
            total_instances = 0
            active_count = 0
            expired_count = 0
            total_pools = len(self.connection_pools)

            for instances in self.all_instances.values():
                for instance in instances:
                    total_instances += 1
                    if instance.is_expired(self.instance_ttl):
                        expired_count += 1
                    else:
                        active_count += 1

            return {
                "total_instances": total_instances,
                "active_instances": active_count,
                "expired_instances": expired_count,
                "total_pools": total_pools,
                "pool_size": self.pool_size,
                "instance_ttl": self.instance_ttl,
                "cleanup_interval": self.cleanup_interval
            }


# Global instance manager
_instance_manager: Optional[DuckDBInstanceManager] = None


async def get_instance_manager() -> DuckDBInstanceManager:
    """Get global instance manager (async)"""
    global _instance_manager
    if _instance_manager is None:
        raise RuntimeError("DuckDBInstanceManager not initialized. Call init_instance_manager() before.")
    return _instance_manager


def init_instance_manager(instance_ttl: int = 600, cleanup_interval: int = 300, pool_size: int = None):
    """Initialize global instance manager"""
    global _instance_manager
    if _instance_manager is None:
        if pool_size is None:
            pool_size = settings.DUCKDB_CONNECTION_POOL_SIZE
        _instance_manager = DuckDBInstanceManager(instance_ttl, cleanup_interval, pool_size)
        _instance_manager.start_cleanup_worker()
        logger.info("Global DuckDBInstanceManager initialized")
    return _instance_manager


async def shutdown_instance_manager():
    """Shutdown global instance manager (async)"""
    global _instance_manager
    if _instance_manager:
        _instance_manager.stop_cleanup_worker()
        await _instance_manager.cleanup_all()
        _instance_manager = None
        logger.info("Global DuckDBInstanceManager shutdown")
