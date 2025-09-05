"""app/db/repository.py"""
from __future__ import annotations

import time
import json
import aiosqlite
from typing import Optional, List
from loguru import logger
from app.models.announcement import Announcement
from app.cache.redis_cache import RedisCache


class AnnouncementRepository:
    def __init__(self, db_path: str, cache: RedisCache, exchanges: List[str]):
        self._db_path = db_path
        self._cache = cache
        self.exchanges = exchanges

        self._log = logger.bind(component="db")

    async def init(self) -> None:
        shema_sql = await self.build_schema()
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(shema_sql)
            await db.commit()

    async def build_schema(self) -> str:
        return "\n".join(
            f"""
            CREATE TABLE IF NOT EXISTS {ex} (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_id TEXT NOT NULL UNIQUE,
              tickers TEXT NOT NULL,
              title TEXT NOT NULL,
              url TEXT NOT NULL,
              published_at_ms INTEGER NOT NULL,
              body_text TEXT,
              classified_type TEXT NOT NULL,
              categories TEXT,
              created_at_ms INTEGER NOT NULL
            );
            """
            for ex in self.exchanges
        )

    def _get_table_name(self, exchange: str) -> str:
        ex = (exchange or "").lower()
        if ex not in self.exchanges:
            raise ValueError(f"Unsupported exchange: {exchange}")
        return ex

    async def insert_many_if_new(self, announcements: List[Announcement]) -> List[Announcement]:
        """
        Checks a batch of announcements against Redis, then inserts the truly new ones
        into the database in a single transaction.
        """
        if not announcements:
            return []

        # Step 1: Efficiently filter out announcements already seen in Redis cache
        new_announcements = await self._cache.filter_new_items(announcements)

        if not new_announcements:
            return []

        # Step 2: Persist the new announcements to the database in a single transaction
        exchange = new_announcements[0].exchange
        table = self._get_table_name(exchange)

        insert_data = [
            (
                ann.source_id,
                json.dumps(ann.tickers),
                ann.title,
                ann.url,
                ann.published_at_ms,
                ann.body_text,
                ann.classified_type.value,
                json.dumps(ann.categories),
                int(time.time() * 1000),
            )
            for ann in new_announcements
        ]

        try:
            async with aiosqlite.connect(self._db_path) as db:
                await db.executemany(
                    f"""
                    INSERT OR IGNORE INTO {table} (
                      source_id, tickers, title, url, published_at_ms,
                      body_text, classified_type, categories, created_at_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    insert_data,
                )
                await db.commit()

            # Step 3: Update the latest timestamp in cache with the newest announcement from the batch
            latest_ann = max(new_announcements, key=lambda ann: ann.published_at_ms)
            await self._cache.set_latest_ms(exchange, latest_ann.published_at_ms)

            self._log.info(f"Inserted {len(new_announcements)} new announcements for {exchange}")
            return new_announcements

        except Exception as e:
            self._log.error(f"db_batch_error: {e}", exchange=exchange)
            # Note: In case of DB error, some items might be in Redis but not DB.
            # The system is self-healing, as they won't be processed again, but it's a trade-off.
            return []

    async def get_latest_published_ms(self, exchange: str) -> Optional[int]:
        """Get from cache first, fallback to DB"""
        latest = await self._cache.get_latest_ms(exchange)
        if latest:
            return latest

        table = self._get_table_name(exchange)
        async with aiosqlite.connect(self._db_path) as db:
            try:
                async with db.execute(f"SELECT MAX(published_at_ms) FROM {table}") as cur:
                    row = await cur.fetchone()
                    latest = int(row[0]) if row and row[0] is not None else None
                    if latest:
                        await self._cache.set_latest_ms(exchange, latest)
                    return latest
            except aiosqlite.OperationalError: # Table might not exist yet
                return None