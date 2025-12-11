import time
import asyncio
import os
import threading
from typing import Dict, Optional
import duckdb
from app.configs.settings import settings
from app.utils import get_logger

logger = get_logger(__name__)


class DuckDBInstance:
    """Wrapper for DuckDB connection with TTL tracking"""
    def __init__(self, user_id: str, access_key: str, secret_key: str):
        self.user_id = user_id
        self.access_key = access_key
        self.secret_key = secret_key
        self.last_used = time.time()
        self.use_count = 0  # Track usage statistics

        self.lock = threading.Lock()
        temp_folder = settings.DUCKDB_TEMP_FOLDER
        self.db_path = os.path.join(temp_folder, f"{user_id}_{os.getpid()}.nonefinity")

        # Create directory if it doesn't exist to store database files
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Initialize DuckDB connection with S3/MinIO configuration
        self._initialize_connection()

    def _initialize_connection(self):
      """Initialize DuckDB connection with S3/MinIO settings"""
      try:
          logger.info("Initializing DuckDB instance for user: %s (PID: %s)", self.user_id, os.getpid())

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

          # --- Prepare User Schema for Isolation ---
          # Sanitize user_id to be a valid schema name (alphanumeric + underscore)
          # ObjectId is usually safe, but we prefix for clarity and safety.
          valid_user_id = self.user_id.replace("-", "_")
          self.metadata_schema = f"user_{valid_user_id}"

          # Create schema if it doesn't exist.
          # We attach Postgres temporarily to run the CREATE SCHEMA command.
          # Note: We rely on the secret created above or pass connection string explicitly if needed.
          try:
              pg_conn_str = f"dbname={settings.POSTGRES_DB} user={settings.POSTGRES_USER} host={settings.POSTGRES_HOST} password={settings.POSTGRES_PASSWORD} port={settings.POSTGRES_PORT}"
              # Attach as a temporary catalog 'pg_init'
              self.con.execute(f"ATTACH '{pg_conn_str}' AS pg_init (TYPE POSTGRES, READ_ONLY FALSE);")
              self.con.execute(f"CREATE SCHEMA IF NOT EXISTS pg_init.{self.metadata_schema};")
              self.con.execute("DETACH pg_init;")
              logger.debug(f"Ensured schema exists: {self.metadata_schema}")
          except Exception as e:
              logger.warning(f"Failed to ensure schema {self.metadata_schema} exists (might already exist or permission error): {e}")
              # We continue, hoping it exists or DuckLake can handle it (though DuckLake usually expects it to exist or defaults to main)

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
                DATA_PATH '{self.data_path}',
                METADATA_SCHEMA '{self.metadata_schema}',
                OVERRIDE_DATA_PATH true
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
    """
    Manage DuckDB instances with TTL and auto cleanup.
    Enforces a strict singleton pattern per user to avoid database file lock conflicts.
    """

    def __init__(self, instance_ttl: int = 600, cleanup_interval: int = 300):
        # Maps user_id -> DuckDBInstance
        self.active_instances: Dict[str, DuckDBInstance] = {}

        # Track ongoing initialization per user to avoid race conditions
        self._pending_init: Dict[str, asyncio.Event] = {}

        self.lock = asyncio.Lock()
        self.instance_ttl = instance_ttl
        self.cleanup_interval = cleanup_interval

        self._cleanup_task = None
        self._stop_cleanup = False

        logger.info(f"DuckDBInstanceManager initialized (TTL: {instance_ttl}s, cleanup: {cleanup_interval}s)")

    async def get_instance(self, user_id: str, access_key: str, secret_key: str) -> DuckDBInstance:
        """
        Get or create DuckDB instance for user.
        Ensures only ONE instance exists per user to prevent file locks.
        """
        while True:
            instance = None
            pending_event = None

            async with self.lock:
                # 1. Check if valid instance exists
                if user_id in self.active_instances:
                    instance = self.active_instances[user_id]
                    if instance.is_expired(self.instance_ttl):
                        logger.debug(f"Instance expired for user {user_id}, closing...")
                        await self._close_and_remove_instance(user_id, instance)
                        instance = None
                    else:
                        instance.update_last_used()
                        instance.use_count += 1
                        return instance

                # 2. Check if initialization is already in progress
                if user_id in self._pending_init:
                    pending_event = self._pending_init[user_id]
                else:
                    # we will be the one to init
                    self._pending_init[user_id] = asyncio.Event()

            # If someone else is initializing, wait for them
            if pending_event:
                logger.debug(f"Waiting for pending initialization for user {user_id}")
                await pending_event.wait()
                continue

            # If we are here, we are the ones initializing
            break

        logger.info(f"Creating new DuckDB instance for user: {user_id}")
        try:
            instance = await asyncio.to_thread(DuckDBInstance, user_id, access_key, secret_key)

            async with self.lock:
                self.active_instances[user_id] = instance
                instance.update_last_used()
                instance.use_count = 1
                return instance
        except Exception as e:
            logger.error(f"Failed to create instance for user {user_id}: {e}")
            raise
        finally:
            # Signal completion
            async with self.lock:
                if user_id in self._pending_init:
                    self._pending_init[user_id].set()
                    del self._pending_init[user_id]

    async def _close_and_remove_instance(self, user_id: str, instance: DuckDBInstance):
        """Helper to safely close and remove an instance."""
        try:
            # Run close in thread to be safe, though typically close() is fast enough
            await asyncio.to_thread(instance.close)
        except Exception as e:
            logger.error(f"Error closing instance for user {user_id}: {e}")

        # Double check it hasn't changed (though called under lock context usually)
        if user_id in self.active_instances and self.active_instances[user_id] == instance:
            del self.active_instances[user_id]

    async def cleanup_expired_instances(self):
        """Cleanup all expired instances"""
        expired_count = 0

        # Snapshot keys to avoid modification during iteration
        # We need to acquire lock to read stable state
        async with self.lock:
            user_ids = list(self.active_instances.keys())

        # Check each user (re-acquire lock for each to minimalize blocking duration)
        for user_id in user_ids:
            async with self.lock:
                if user_id in self.active_instances:
                    instance = self.active_instances[user_id]
                    if instance.is_expired(self.instance_ttl):
                        await self._close_and_remove_instance(user_id, instance)
                        expired_count += 1

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
        """Background async worker loop"""
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
        """Cleanup all instances (shutdown)"""
        async with self.lock:
            user_ids = list(self.active_instances.keys())
            for user_id in user_ids:
                if user_id in self.active_instances:
                    await self._close_and_remove_instance(user_id, self.active_instances[user_id])
        logger.info("Cleaned up all DuckDB instances")

    async def cleanup_user(self, user_id: str):
        """Cleanup user resources: instance, local DB file, and Postgres schema"""
        logger.info(f"Cleaning up DuckDB resources for user {user_id}")

        # 1. Close active instance if any
        async with self.lock:
            if user_id in self.active_instances:
                instance = self.active_instances[user_id]
                await self._close_and_remove_instance(user_id, instance)

        # 2. Delete local DB file (best effort)
        # Note: We don't track the exact PID of the file if the instance is not active.
        # But we can try to find files matching the pattern.
        temp_folder = settings.DUCKDB_TEMP_FOLDER
        try:
             import glob
             files = glob.glob(os.path.join(temp_folder, f"{user_id}_*.nonefinity"))
             for f in files:
                 try:
                     os.remove(f)
                     logger.info(f"Deleted local DB file: {f}")
                 except Exception as e:
                     logger.warning(f"Failed to delete local DB file {f}: {e}")
        except Exception as e:
            logger.warning(f"Error cleaning up local DB files for user {user_id}: {e}")

        # 3. Drop Postgres Schema
        try:
             # Create a transient ephemeral DuckDB connection just for this op
            con = duckdb.connect(database=":memory:")
            con.execute("INSTALL postgres; LOAD postgres;")

            pg_conn_str = f"dbname={settings.POSTGRES_DB} user={settings.POSTGRES_USER} host={settings.POSTGRES_HOST} password={settings.POSTGRES_PASSWORD} port={settings.POSTGRES_PORT}"

            # Attach with read_write access
            con.execute(f"ATTACH '{pg_conn_str}' AS pg_cleanup (TYPE POSTGRES, READ_ONLY FALSE);")
            valid_user_id = user_id.replace("-", "_")
            schema_name = f"user_{valid_user_id}"

            con.execute(f"DROP SCHEMA IF EXISTS pg_cleanup.{schema_name} CASCADE;")
            con.close()
            logger.info(f"Dropped schema {schema_name} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to drop schema for user {user_id}: {e}")

    async def get_stats(self) -> dict:
        """Get statistics about current instances"""
        async with self.lock:
            total_instances = len(self.active_instances)
            expired_count = sum(1 for inst in self.active_instances.values() if inst.is_expired(self.instance_ttl))

            return {
                "total_instances": total_instances,
                "active_instances": total_instances - expired_count,
                "expired_instances": expired_count,
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
        # pool_size is ignored now, kept for backward compatibility if needed
        _instance_manager = DuckDBInstanceManager(instance_ttl, cleanup_interval)
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

