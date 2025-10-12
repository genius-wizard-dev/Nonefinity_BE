import time
import threading
import os
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
          extensions = ["aws", "httpfs", "parquet", "ducklake", "postgres"]
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
    """Manage cache DuckDB instances with TTL and auto cleanup"""

    def __init__(self, instance_ttl: int = 600, cleanup_interval: int = 300):
        self.instances: Dict[str, DuckDBInstance] = {}
        self.lock = threading.Lock()
        self.instance_ttl = instance_ttl  # 10 minutes
        self.cleanup_interval = cleanup_interval  # 5 minutes
        self._cleanup_thread = None
        self._stop_cleanup = False

        logger.info(f"DuckDBInstanceManager initialized with TTL: {instance_ttl}s, cleanup interval: {cleanup_interval}s")

    def get_instance(self, user_id: str, access_key: str, secret_key: str) -> DuckDBInstance:
        """
        Get or create DuckDB instance for user

        Args:
            user_id: ID of user
            access_key: MinIO access key
            secret_key: MinIO secret key

        Returns:
            DuckDBInstance: Instance cached or newly created
        """
        with self.lock:
            # Check if instance exists
            if user_id in self.instances:
                instance = self.instances[user_id]

                # Check if instance has expired
                if not instance.is_expired(self.instance_ttl):
                    # Reset TTL and return current instance
                    instance.update_last_used()
                    logger.debug(f"Using cached instance for user: {user_id}")
                    return instance
                else:
                    # Instance expired, cleanup and create new
                    logger.info(f"Instance expired for user: {user_id}, creating new")
                    self._cleanup_instance(user_id)

            # Create new instance
            logger.info(f"Creating new DuckDB instance for user: {user_id}")
            instance = DuckDBInstance(user_id, access_key, secret_key)
            self.instances[user_id] = instance

            return instance

    def _cleanup_instance(self, user_id: str):
        """Cleanup a specific instance (called with lock)"""
        if user_id in self.instances:
            try:
                self.instances[user_id].close()
                del self.instances[user_id]
                logger.info(f"Cleaned up instance for user: {user_id}")
            except Exception as e:
                logger.error(f"Error cleaning up instance for user {user_id}: {str(e)}")

    def cleanup_expired_instances(self):
        """Cleanup all expired instances"""
        expired_users = []

        with self.lock:
            for user_id, instance in list(self.instances.items()):
                if instance.is_expired(self.instance_ttl):
                    expired_users.append(user_id)

            # Cleanup expired instances
            for user_id in expired_users:
                self._cleanup_instance(user_id)

        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired instances")

    def start_cleanup_worker(self):
        """Start background worker to cleanup expired instances"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup = False
            self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self._cleanup_thread.start()
            logger.info("Background cleanup worker started")

    def stop_cleanup_worker(self):
        """Stop background cleanup worker"""
        self._stop_cleanup = True
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
            logger.info("Background cleanup worker stopped")

    def _cleanup_worker(self):
        """Background worker to cleanup expired instances"""
        logger.info("Background cleanup worker started")

        while not self._stop_cleanup:
            try:
                time.sleep(self.cleanup_interval)
                if not self._stop_cleanup:
                    self.cleanup_expired_instances()
            except Exception as e:
                logger.error(f"Error in cleanup worker: {str(e)}")

    def cleanup_all(self):
        """Cleanup all instances (used when shutting down app)"""
        with self.lock:
            for user_id in list(self.instances.keys()):
                self._cleanup_instance(user_id)

        logger.info("Cleaned up all DuckDB instances")

    def get_stats(self) -> dict:
        """Get statistics about current instances"""
        with self.lock:
            active_count = 0
            expired_count = 0

            for instance in self.instances.values():
                if instance.is_expired(self.instance_ttl):
                    expired_count += 1
                else:
                    active_count += 1

            return {
                "total_instances": len(self.instances),
                "active_instances": active_count,
                "expired_instances": expired_count,
                "instance_ttl": self.instance_ttl,
                "cleanup_interval": self.cleanup_interval
            }


# Global instance manager
_instance_manager: Optional[DuckDBInstanceManager] = None


def get_instance_manager() -> DuckDBInstanceManager:
    """Get global instance manager"""
    global _instance_manager
    if _instance_manager is None:
        raise RuntimeError("DuckDBInstanceManager not initialized. Call init_instance_manager() before.")
    return _instance_manager


def init_instance_manager(instance_ttl: int = 600, cleanup_interval: int = 300):
    """Initialize global instance manager"""
    global _instance_manager
    if _instance_manager is None:
        _instance_manager = DuckDBInstanceManager(instance_ttl, cleanup_interval)
        _instance_manager.start_cleanup_worker()
        logger.info("Global DuckDBInstanceManager initialized")
    return _instance_manager


def shutdown_instance_manager():
    """Shutdown global instance manager"""
    global _instance_manager
    if _instance_manager:
        _instance_manager.stop_cleanup_worker()
        _instance_manager.cleanup_all()
        _instance_manager = None
        logger.info("Global DuckDBInstanceManager shutdown")
