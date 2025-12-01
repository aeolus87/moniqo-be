"""
Redis Cache Utilities

Simple Redis client wrapper for caching operations.

Author: Moniqo Team
Last Updated: 2025-11-22
"""

import redis.asyncio as redis
from typing import Optional
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance.
    
    Returns:
        Redis client
        
    Example:
        redis_client = await get_redis_client()
        await redis_client.set("key", "value")
        value = await redis_client.get("key")
    """
    global _redis_client
    
    if _redis_client is None:
        settings = get_settings()
        
        try:
            _redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            
            # Test connection
            await _redis_client.ping()
            
            logger.info(f"Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    return _redis_client


async def close_redis_client():
    """Close Redis client connection"""
    global _redis_client
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from prefix and arguments.
    
    Args:
        prefix: Key prefix
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
        
    Returns:
        Cache key string
        
    Example:
        generate_cache_key("user", 123, status="active")
        # Returns: "user:123:status=active"
    """
    parts = [prefix]
    
    # Add positional args
    for arg in args:
        parts.append(str(arg))
    
    # Add keyword args (sorted for consistency)
    for key in sorted(kwargs.keys()):
        parts.append(f"{key}={kwargs[key]}")
    
    return ":".join(parts)


async def get_cache(key: str, default=None):
    """
    Get value from cache.
    
    Args:
        key: Cache key
        default: Default value if key not found
        
    Returns:
        Cached value or default
    """
    try:
        redis_client = await get_redis_client()
        value = await redis_client.get(key)
        return value if value is not None else default
    except Exception as e:
        logger.error(f"Failed to get cache key {key}: {str(e)}")
        return default


async def set_cache(key: str, value: str, ttl: int = 3600):
    """
    Set value in cache with TTL.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (default: 1 hour)
    """
    try:
        redis_client = await get_redis_client()
        await redis_client.set(key, value, ex=ttl)
    except Exception as e:
        logger.error(f"Failed to set cache key {key}: {str(e)}")


async def delete_cache(key: str):
    """
    Delete value from cache.
    
    Args:
        key: Cache key to delete
    """
    try:
        redis_client = await get_redis_client()
        await redis_client.delete(key)
    except Exception as e:
        logger.error(f"Failed to delete cache key {key}: {str(e)}")


async def delete_cache_pattern(pattern: str):
    """
    Delete all keys matching a pattern.
    
    Args:
        pattern: Pattern to match (e.g., "user:*")
    """
    try:
        redis_client = await get_redis_client()
        keys = await redis_client.keys(pattern)
        if keys:
            await redis_client.delete(*keys)
    except Exception as e:
        logger.error(f"Failed to delete cache pattern {pattern}: {str(e)}")


async def cache_exists(key: str) -> bool:
    """
    Check if cache key exists.
    
    Args:
        key: Cache key to check
        
    Returns:
        True if key exists
    """
    try:
        redis_client = await get_redis_client()
        return await redis_client.exists(key) > 0
    except Exception as e:
        logger.error(f"Failed to check cache key {key}: {str(e)}")
        return False


async def get_cache_ttl(key: str) -> Optional[int]:
    """
    Get remaining TTL for a cache key.
    
    Args:
        key: Cache key
        
    Returns:
        TTL in seconds, or None if key doesn't exist or has no expiry
    """
    try:
        redis_client = await get_redis_client()
        ttl = await redis_client.ttl(key)
        return ttl if ttl > 0 else None
    except Exception as e:
        logger.error(f"Failed to get TTL for key {key}: {str(e)}")
        return None


class CacheManager:
    """
    Simple cache manager for common caching patterns.
    
    Usage:
        cache = CacheManager(prefix="user")
        await cache.set("123", {"name": "Alice"}, ttl=3600)
        user = await cache.get("123")
    """
    
    def __init__(self, prefix: str = ""):
        """
        Initialize cache manager.
        
        Args:
            prefix: Prefix for all cache keys
        """
        self.prefix = prefix
    
    def _make_key(self, key: str) -> str:
        """Generate full cache key with prefix"""
        return f"{self.prefix}:{key}" if self.prefix else key
    
    async def get(self, key: str, default=None):
        """Get value from cache"""
        return await get_cache(self._make_key(key), default)
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache"""
        await set_cache(self._make_key(key), value, ttl)
    
    async def delete(self, key: str):
        """Delete value from cache"""
        await delete_cache(self._make_key(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await cache_exists(self._make_key(key))
    
    async def ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL"""
        return await get_cache_ttl(self._make_key(key))
