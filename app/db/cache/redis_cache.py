"""app/cache/redis_cache.py"""
from typing import Optional, List
import redis.asyncio as redis
from loguru import logger
from app.core.models import Announcement


class RedisCache:
    """Redis cache for fast deduplication"""

    def __init__(self, redis_url: str = "redis://localhost:6379", use_fakeredis: bool = False):
        self._log = logger.bind(component="cache")

        if use_fakeredis:
            import fakeredis.aioredis
            self._redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        else:
            self._redis = redis.from_url(redis_url, decode_responses=True)

    async def is_new(self, exchange: str, source_id: str) -> bool:
        """Check if announcement is new and reserve it atomically"""
        key = f"ann:{exchange}:{source_id}"
        # SETNX returns True if key was set (didn't exist)
        result = await self._redis.set(key, "1", nx=True, ex=86400 * 7)  # 7 days TTL
        return bool(result)

    async def filter_new_items(self, announcements: List[Announcement]) -> List[Announcement]:
        """
        Efficiently filters a list of announcements, returning only the ones not already in the cache.
        This uses a pipeline to minimize round-trips to Redis.
        """
        if not announcements:
            return []

        # Assume all are from the same exchange, which is true in our case.
        exchange = announcements[0].exchange

        pipe = self._redis.pipeline()
        for ann in announcements:
            key = f"ann:{exchange}:{ann.source_id}"
            pipe.set(key, "1", nx=True, ex=86400 * 7)

        # The result will be a list of booleans (True if the key was new, False otherwise)
        results = await pipe.execute()

        # Return only the announcements that were successfully set (i.e., were new)
        new_announcements = [ann for ann, is_new in zip(announcements, results) if is_new]
        return new_announcements

    async def get_latest_ms(self, exchange: str) -> Optional[int]:
        """Get latest published timestamp for exchange"""
        key = f"latest:{exchange}"
        value = await self._redis.get(key)
        return int(value) if value else None

    async def set_latest_ms(self, exchange: str, timestamp_ms: int):
        """Update latest published timestamp"""
        key = f"latest:{exchange}"
        current = await self.get_latest_ms(exchange)
        if not current or timestamp_ms > current:
            await self._redis.set(key, str(timestamp_ms), ex=86400 * 30)  # 30 days

    async def close(self):
        await self._redis.close()