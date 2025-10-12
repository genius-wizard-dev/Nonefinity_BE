
from functools import wraps
from typing import Callable, Optional, Union
from datetime import timedelta
from app.services.redis_service import redis_service, list_cache_key
from app.utils import get_logger

logger = get_logger(__name__)


def cache_list(
    prefix: str,
    ttl: Union[int, timedelta] = 300,  # 5 minutes default
    skip_cache: bool = False
):
    """
    Decorator to cache list method results

    Args:
        prefix: Cache key prefix (e.g., 'datasets', 'models', 'credentials')
        ttl: Time to live in seconds or timedelta object
        skip_cache: If True, skip cache and always fetch fresh data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from the first argument (current_user dict)
            current_user = args[0] if args else kwargs.get('current_user')
            if not current_user or 'user_id' not in current_user:
                logger.warning("No user_id found in cache decorator, skipping cache")
                return await func(*args, **kwargs)

            user_id = current_user['user_id']

            # Extract pagination and filter parameters
            skip = kwargs.get('skip', 0)
            limit = kwargs.get('limit', 100)

            # Extract filter parameters (exclude function-specific params)
            exclude_params = {'current_user', 'skip', 'limit'}
            filters = {k: v for k, v in kwargs.items() if k not in exclude_params}

            # Generate cache key
            cache_key = list_cache_key(prefix, user_id, skip=skip, limit=limit, **filters)

            # Try to get from cache first (unless skip_cache is True)
            if not skip_cache:
                try:
                    cached_result = await redis_service.get(cache_key)
                    if cached_result is not None:
                        logger.info(f"Cache hit for {cache_key}")
                        return cached_result
                except Exception as e:
                    logger.error(f"Error getting from cache: {e}")

            # Cache miss or error - fetch fresh data
            logger.info(f"Cache miss for {cache_key}, fetching fresh data")
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                await redis_service.set(cache_key, result, ttl)
                logger.info(f"Cached result for {cache_key}")
            except Exception as e:
                logger.error(f"Error caching result: {e}")

            return result

        return wrapper
    return decorator


def invalidate_cache(prefix: str, user_id: Optional[str] = None):
    """
    Decorator to invalidate cache when data changes

    Args:
        prefix: Cache key prefix to invalidate
        user_id: Specific user_id to invalidate (if None, invalidates all users)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute the original function
            result = await func(*args, **kwargs)

            # Invalidate cache after successful operation
            try:
                if user_id:
                    # Invalidate for specific user
                    pattern = f"{prefix}:{user_id}:*"
                else:
                    # Invalidate for all users
                    pattern = f"{prefix}:*"

                deleted_count = await redis_service.delete_pattern(pattern)
                logger.info(f"Invalidated {deleted_count} cache entries for pattern {pattern}")

            except Exception as e:
                logger.error(f"Error invalidating cache: {e}")

            return result

        return wrapper
    return decorator


async def invalidate_user_cache(prefix: str, user_id: str):
    """Manually invalidate cache for a specific user and prefix"""
    try:
        pattern = f"{prefix}:{user_id}:*"
        deleted_count = await redis_service.delete_pattern(pattern)
        logger.info(f"Manually invalidated {deleted_count} cache entries for user {user_id}, prefix {prefix}")
        return deleted_count
    except Exception as e:
        logger.error(f"Error manually invalidating cache: {e}")
        return 0


async def invalidate_all_cache(prefix: str):
    """Manually invalidate all cache entries for a prefix"""
    try:
        pattern = f"{prefix}:*"
        deleted_count = await redis_service.delete_pattern(pattern)
        logger.info(f"Manually invalidated {deleted_count} cache entries for prefix {prefix}")
        return deleted_count
    except Exception as e:
        logger.error(f"Error manually invalidating all cache: {e}")
        return 0
