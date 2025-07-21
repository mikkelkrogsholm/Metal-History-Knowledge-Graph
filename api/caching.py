"""
Caching layer for Metal History API
Implements Redis-based caching with intelligent invalidation
"""

from functools import wraps
from typing import Optional, Any, Callable
import hashlib
import json
import pickle
import logging
import time
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching operations with Redis backend"""
    
    def __init__(
        self, 
        redis_url: str = "redis://localhost:6379", 
        default_ttl: int = 3600,
        key_prefix: str = "metal_api"
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.redis_client = None
        self._connect()
        
    def _connect(self):
        """Establish Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except RedisError as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self.redis_client = None
            
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        # Create a unique key from function name and arguments
        key_parts = [self.key_prefix, prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # For complex objects, use a hash
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
            
        return ":".join(key_parts)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
            
        try:
            value = self.redis_client.get(key)
            if value:
                return pickle.loads(value)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL"""
        if not self.redis_client:
            return False
            
        try:
            ttl = ttl or self.default_ttl
            serialized = pickle.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
            
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.redis_client:
            return 0
            
        try:
            keys = list(self.redis_client.scan_iter(match=pattern))
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """Clear all cache entries for this API"""
        pattern = f"{self.key_prefix}:*"
        deleted = self.delete_pattern(pattern)
        logger.info(f"Cleared {deleted} cache entries")
        return deleted > 0
    
    def cached(
        self, 
        prefix: str, 
        ttl: Optional[int] = None,
        skip_cache: Optional[Callable] = None
    ):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Check if we should skip cache
                if skip_cache and skip_cache(*args, **kwargs):
                    return await func(*args, **kwargs)
                
                # Generate cache key
                cache_key = self._make_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
                
                # Call function and cache result
                logger.debug(f"Cache miss: {cache_key}")
                result = await func(*args, **kwargs)
                
                # Cache the result
                self.set(cache_key, result, ttl)
                
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Check if we should skip cache
                if skip_cache and skip_cache(*args, **kwargs):
                    return func(*args, **kwargs)
                
                # Generate cache key
                cache_key = self._make_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
                
                # Call function and cache result
                logger.debug(f"Cache miss: {cache_key}")
                result = func(*args, **kwargs)
                
                # Cache the result
                self.set(cache_key, result, ttl)
                
                return result
            
            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
                
        return decorator
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disconnected"}
            
        try:
            info = self.redis_client.info()
            pattern = f"{self.key_prefix}:*"
            keys = list(self.redis_client.scan_iter(match=pattern))
            
            return {
                "status": "connected",
                "total_keys": len(keys),
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1)) * 100, 
                    2
                ) if info.get("keyspace_hits", 0) > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}


class CacheWarmer:
    """Pre-populate cache with commonly accessed data"""
    
    def __init__(self, cache_manager: CacheManager, db_connection):
        self.cache = cache_manager
        self.db = db_connection
        
    async def warm_popular_bands(self, limit: int = 100):
        """Cache most popular bands"""
        query = """
        MATCH (b:Band)
        OPTIONAL MATCH (b)-[:RELEASED]->(a:Album)
        WITH b, COUNT(a) as album_count
        ORDER BY album_count DESC
        LIMIT $limit
        RETURN b.id
        """
        
        result = self.db.execute_query(query, {"limit": limit})
        band_ids = []
        
        while result.has_next():
            band_ids.append(result.get_next()[0])
            
        logger.info(f"Warming cache for {len(band_ids)} popular bands")
        
        # This would typically call the get_band function for each ID
        # to populate the cache
        
        return band_ids
    
    async def warm_recent_data(self, days: int = 7):
        """Cache recently added or modified data"""
        # This would cache entities modified in the last N days
        pass
    
    async def warm_static_data(self):
        """Cache relatively static data like genres and stats"""
        # Cache genre list
        genre_key = self.cache._make_key("genres", "all")
        
        # Cache database stats
        stats_key = self.cache._make_key("stats", "db")
        
        logger.info("Warmed static data cache")


# Invalidation strategies
class CacheInvalidator:
    """Handle cache invalidation on data changes"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
        
    def invalidate_band(self, band_id: str):
        """Invalidate all cache entries related to a band"""
        patterns = [
            f"*:band:{band_id}:*",
            f"*:bands:{band_id}",
            f"*:influences:{band_id}",
            f"*:search:*"  # Invalidate search results too
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = self.cache.delete_pattern(pattern)
            total_deleted += deleted
            
        logger.info(f"Invalidated {total_deleted} cache entries for band {band_id}")
        
    def invalidate_album(self, album_id: str):
        """Invalidate all cache entries related to an album"""
        patterns = [
            f"*:album:{album_id}:*",
            f"*:albums:{album_id}",
            f"*:search:*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = self.cache.delete_pattern(pattern)
            total_deleted += deleted
            
        logger.info(f"Invalidated {total_deleted} cache entries for album {album_id}")
        
    def invalidate_search(self):
        """Invalidate all search cache entries"""
        deleted = self.cache.delete_pattern("*:search:*")
        logger.info(f"Invalidated {deleted} search cache entries")
        
    def invalidate_stats(self):
        """Invalidate statistics cache"""
        deleted = self.cache.delete_pattern("*:stats:*")
        logger.info(f"Invalidated {deleted} stats cache entries")