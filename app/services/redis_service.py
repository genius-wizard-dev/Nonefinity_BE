import json
from typing import Any, Optional, Union
from datetime import timedelta
import redis.asyncio as redis
from redis.commands.json.path import Path
from app.configs.settings import settings
from app.utils import get_logger

logger = get_logger(__name__)


class RedisService:
    """Redis service for caching operations"""

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

    async def get_client(self) -> redis.Redis:
        """Get Redis client instance"""
        if self._redis_client is None:
            await self._connect()
        return self._redis_client

    async def _connect(self):
        """Establish Redis connection"""
        try:
            # Create connection pool
            self._connection_pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=True,
                max_connections=20
            )

            # Create Redis client
            self._redis_client = redis.Redis(connection_pool=self._connection_pool)

            # Test connection
            await self._redis_client.ping()
            logger.info("Redis connection established successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """Set value in cache with optional TTL"""
        try:
            client = await self.get_client()
            serialized_value = json.dumps(value, default=str)

            if ttl:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                await client.setex(key, ttl, serialized_value)
            else:
                await client.set(key, serialized_value)

            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            client = await self.get_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            client = await self.get_client()
            keys = await client.keys(pattern)
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error deleting cache pattern {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await self.get_client()
            result = await client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """Get TTL for key"""
        try:
            client = await self.get_client()
            return await client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {e}")
            return -1

    async def jset(self, key, value, ex=None):
        """Set JSON value in Redis with optional expiration (ex in seconds)."""
        try:
            client = await self.get_client()
            await client.json().set(key, Path.root_path(), value)
            if ex:
                await client.expire(key, ex)
            return True
        except Exception as e:
            logger.error(f"Error setting JSON for key {key}: {e}")
            return False

    async def jget(self, key):
        """Get JSON value from Redis."""
        try:
            client = await self.get_client()
            return await client.json().get(key, Path.root_path())
        except Exception as e:
            logger.error(f"Error getting JSON for key {key}: {e}")
            return None


# Global Redis service instance
redis_service = RedisService()


def cache_key(prefix: str, user_id: str, **kwargs) -> str:
    """Generate cache key with prefix and parameters"""
    # Sort kwargs for consistent key generation
    sorted_kwargs = sorted(kwargs.items())
    params = "_".join([f"{k}:{v}" for k, v in sorted_kwargs if v is not None])

    if params:
        return f"{prefix}:{user_id}:{params}"
    return f"{prefix}:{user_id}"


def list_cache_key(prefix: str, user_id: str, skip: int = 0, limit: int = 100, **filters) -> str:
    """Generate cache key for list operations"""
    # Remove None values and sort for consistent key generation
    clean_filters = {k: v for k, v in filters.items() if v is not None}
    return cache_key(prefix, user_id, skip=skip, limit=limit, **clean_filters)
