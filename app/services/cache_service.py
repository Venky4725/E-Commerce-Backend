"""
Cache service using Redis
"""
import json
import logging
import time
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

class CacheService:
    _last_redis_check = 0.0
    _redis_available = False
    _redis_warning_logged = False
    _check_interval_seconds = 5.0

    @staticmethod
    async def _is_redis_available() -> bool:
        """Check if Redis is available"""
        now = time.monotonic()
        if now - CacheService._last_redis_check < CacheService._check_interval_seconds:
            return CacheService._redis_available

        CacheService._last_redis_check = now
        try:
            if redis_client.ping():
                CacheService._redis_available = True
                CacheService._redis_warning_logged = False
                return True
        except Exception as exc:
            CacheService._redis_available = False
            if not CacheService._redis_warning_logged:
                logger.warning("Redis unavailable at configured URL; cache bypassed: %s", exc)
                CacheService._redis_warning_logged = True
            return False
        CacheService._redis_available = False
        return False
    
    @staticmethod
    async def set(key: str, value: dict, expire: int = 3600):
        """Set cache value with expiration"""
        # Check if Redis is available before attempting to cache
        if not await CacheService._is_redis_available():
            # Return early if Redis unavailable - no caching
            return
        
        try:
            # Convert value to JSON string and store in Redis
            serialized_value = json.dumps(value)
            # Direct access should work fine for Redis operations 
            redis_client.setex(key, expire, serialized_value)
        except Exception as e:
            logger.error(f"Failed to cache to Redis: {e}")
    
    @staticmethod
    async def get(key: str) -> dict:
        """Get cached value"""
        # Check if Redis is available before attempting to retrieve
        if not await CacheService._is_redis_available():
            # Return None if Redis unavailable - no cache hit
            return None
            
        try:
            # Get value from Redis
            value = redis_client.get(key)
            if value:
                # Parse JSON back to dict
                parsed_value = json.loads(value)
                return parsed_value
        except Exception as e:
            logger.error(f"Failed to retrieve from Redis: {e}")
        return None
    
    @staticmethod
    async def delete(key: str):
        """Delete cached value"""
        # Check if Redis is available before attempting to delete
        if not await CacheService._is_redis_available():
            return
            
        try:
            redis_client.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete from Redis: {e}")
