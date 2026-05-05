"""
Generic cache service using Redis with automatic DB fallback.
Uses the shared is_redis_available() helper so availability checks
are consistent across the whole app.
"""
import json
import logging

from app.core.redis_client import redis_client, is_redis_available

logger = logging.getLogger(__name__)


class CacheService:

    @staticmethod
    async def set(key: str, value: dict, expire: int = 3600) -> None:
        """Cache a dict value. Silently skipped if Redis is unavailable."""
        if not await is_redis_available():
            return
        try:
            await redis_client.setex(key, expire, json.dumps(value))
        except Exception as exc:
            logger.warning("Redis SET failed (ignored): %s", exc)

    @staticmethod
    async def get(key: str) -> dict | None:
        """Retrieve a cached dict. Returns None on miss or Redis unavailability."""
        if not await is_redis_available():
            return None
        try:
            raw = await redis_client.get(key)
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis GET failed (ignored): %s", exc)
        return None

    @staticmethod
    async def delete(key: str) -> None:
        """Delete a cached key. Silently skipped if Redis is unavailable."""
        if not await is_redis_available():
            return
        try:
            await redis_client.delete(key)
        except Exception as exc:
            logger.warning("Redis DELETE failed (ignored): %s", exc)
