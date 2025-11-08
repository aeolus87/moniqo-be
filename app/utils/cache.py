"""
Redis caching utilities.

Provides cache operations with TTL management and key pattern deletion.
"""

import json
import hashlib
from typing import Any, Optional
import redis.asyncio as aioredis
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global Redis client
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Get or create Redis client.
    
    Returns:
        aioredis.Redis: Redis client instance
        
    Raises:
        RuntimeError: If Redis connection fails
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            # Test connection
            await _redis_client.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise RuntimeError(f"Redis connection failed: {str(e)}")
    
    return _redis_client


async def close_redis_connection() -> None:
    """
    Close Redis connection.
    
    Called during application shutdown.
    """
    global _redis_client
    
    if _redis_client:
        logger.info("Closing Redis connection")
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def generate_cache_key(*args: Any, prefix: str = "") -> str:
    """
    Generate cache key from arguments.
    
    Creates a consistent cache key by hashing arguments.
    
    Args:
        *args: Arguments to include in cache key
        prefix: Prefix for the cache key (e.g., "users:list")
        
    Returns:
        str: Generated cache key
        
    Example:
        >>> generate_cache_key("users", "list", limit=10, offset=0, prefix="api")
        "api:users:list:e3b0c44298fc1c"
    """
    # Convert args to string
    args_str = ":".join(str(arg) for arg in args if arg)
    
    # Create hash of arguments for consistency
    args_hash = hashlib.md5(args_str.encode()).hexdigest()[:14]
    
    # Combine prefix and hash
    if prefix:
        return f"{prefix}:{args_hash}"
    return args_hash


async def get_cache(key: str) -> Optional[Any]:
    """
    Get value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Any: Cached value (deserialized from JSON) or None if not found
        
    Example:
        >>> await get_cache("users:list:limit=10&offset=0")
        {"items": [...], "total": 150}
    """
    try:
        client = await get_redis_client()
        value = await client.get(key)
        
        if value is None:
            logger.debug(f"Cache miss: {key}")
            return None
        
        logger.debug(f"Cache hit: {key}")
        return json.loads(value)
        
    except Exception as e:
        logger.error(f"Error getting cache key {key}: {str(e)}")
        return None


async def set_cache(
    key: str,
    value: Any,
    ttl: Optional[int] = None
) -> bool:
    """
    Set value in cache.
    
    Args:
        key: Cache key
        value: Value to cache (will be serialized to JSON)
        ttl: Time to live in seconds (default: REDIS_TTL_SECONDS from settings)
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        >>> await set_cache("users:list:limit=10", {"items": [...], "total": 150})
        True
    """
    try:
        client = await get_redis_client()
        
        # Serialize value to JSON
        serialized_value = json.dumps(value)
        
        # Use default TTL if not specified
        if ttl is None:
            ttl = settings.REDIS_TTL_SECONDS
        
        # Set with expiration
        await client.setex(key, ttl, serialized_value)
        
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
        return True
        
    except Exception as e:
        logger.error(f"Error setting cache key {key}: {str(e)}")
        return False


async def delete_cache(key: str) -> bool:
    """
    Delete value from cache.
    
    Args:
        key: Cache key to delete
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        >>> await delete_cache("users:list:limit=10")
        True
    """
    try:
        client = await get_redis_client()
        deleted_count = await client.delete(key)
        
        if deleted_count > 0:
            logger.debug(f"Cache deleted: {key}")
            return True
        
        logger.debug(f"Cache key not found: {key}")
        return False
        
    except Exception as e:
        logger.error(f"Error deleting cache key {key}: {str(e)}")
        return False


async def delete_cache_pattern(pattern: str) -> int:
    """
    Delete all cache keys matching pattern.
    
    Useful for cache invalidation (e.g., "users:*" to clear all user caches).
    
    Args:
        pattern: Key pattern (supports wildcards, e.g., "users:*")
        
    Returns:
        int: Number of keys deleted
        
    Example:
        >>> await delete_cache_pattern("users:*")
        15  # Deleted 15 keys
    """
    try:
        client = await get_redis_client()
        
        # Find all keys matching pattern
        keys = []
        async for key in client.scan_iter(match=pattern, count=100):
            keys.append(key)
        
        if not keys:
            logger.debug(f"No cache keys found for pattern: {pattern}")
            return 0
        
        # Delete all matching keys
        deleted_count = await client.delete(*keys)
        
        logger.info(f"Cache pattern deleted: {pattern} ({deleted_count} keys)")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error deleting cache pattern {pattern}: {str(e)}")
        return 0


async def cache_exists(key: str) -> bool:
    """
    Check if cache key exists.
    
    Args:
        key: Cache key to check
        
    Returns:
        bool: True if key exists, False otherwise
        
    Example:
        >>> await cache_exists("users:list:limit=10")
        True
    """
    try:
        client = await get_redis_client()
        exists = await client.exists(key)
        return bool(exists)
        
    except Exception as e:
        logger.error(f"Error checking cache key {key}: {str(e)}")
        return False


async def get_cache_ttl(key: str) -> Optional[int]:
    """
    Get remaining TTL for cache key.
    
    Args:
        key: Cache key
        
    Returns:
        int: Remaining TTL in seconds, or None if key doesn't exist
        
    Example:
        >>> await get_cache_ttl("users:list:limit=10")
        85000  # 85000 seconds remaining
    """
    try:
        client = await get_redis_client()
        ttl = await client.ttl(key)
        
        if ttl < 0:
            # -1 means no expiration, -2 means key doesn't exist
            return None
        
        return ttl
        
    except Exception as e:
        logger.error(f"Error getting TTL for cache key {key}: {str(e)}")
        return None


class CacheManager:
    """
    Cache manager for module-specific caching.
    
    Provides a convenient interface for caching with module prefix.
    
    Attributes:
        module: Module name (used as cache key prefix)
    """
    
    def __init__(self, module: str):
        """
        Initialize CacheManager.
        
        Args:
            module: Module name (e.g., "users", "roles")
        """
        self.module = module
    
    def _get_key(self, operation: str, **kwargs) -> str:
        """
        Generate cache key for module operation.
        
        Args:
            operation: Operation name (e.g., "list", "detail")
            **kwargs: Additional parameters
            
        Returns:
            str: Cache key
        """
        # Create params string
        params = "&".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{self.module}:{operation}:{params}" if params else f"{self.module}:{operation}"
    
    async def get(self, operation: str, **kwargs) -> Optional[Any]:
        """
        Get cached value for operation.
        
        Args:
            operation: Operation name
            **kwargs: Operation parameters
            
        Returns:
            Any: Cached value or None
        """
        key = self._get_key(operation, **kwargs)
        return await get_cache(key)
    
    async def set(self, operation: str, value: Any, ttl: Optional[int] = None, **kwargs) -> bool:
        """
        Set cached value for operation.
        
        Args:
            operation: Operation name
            value: Value to cache
            ttl: Time to live in seconds
            **kwargs: Operation parameters
            
        Returns:
            bool: True if successful
        """
        key = self._get_key(operation, **kwargs)
        return await set_cache(key, value, ttl)
    
    async def delete(self, operation: str, **kwargs) -> bool:
        """
        Delete cached value for operation.
        
        Args:
            operation: Operation name
            **kwargs: Operation parameters
            
        Returns:
            bool: True if successful
        """
        key = self._get_key(operation, **kwargs)
        return await delete_cache(key)
    
    async def invalidate_all(self) -> int:
        """
        Invalidate all caches for this module.
        
        Returns:
            int: Number of keys deleted
        """
        pattern = f"{self.module}:*"
        return await delete_cache_pattern(pattern)

