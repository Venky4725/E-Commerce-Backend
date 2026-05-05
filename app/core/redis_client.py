"""
Redis client setup with availability helper
"""
import logging
import time

import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
)

# ── Availability cache (avoid hammering Redis on every request) ────────────────
_last_check: float = 0.0
_available: bool = False
_CHECK_INTERVAL: float = 5.0  # seconds between liveness probes


async def is_redis_available() -> bool:
    """
    Returns True if Redis is reachable.
    Result is cached for _CHECK_INTERVAL seconds so we don't ping on every call.
    """
    global _last_check, _available

    now = time.monotonic()
    if now - _last_check < _CHECK_INTERVAL:
        return _available

    _last_check = now
    try:
        await redis_client.ping()
        if not _available:
            logger.info("Redis is now available.")
        _available = True
    except Exception as exc:
        if _available:
            logger.warning("Redis became unavailable; falling back to DB. Error: %s", exc)
        _available = False

    return _available
