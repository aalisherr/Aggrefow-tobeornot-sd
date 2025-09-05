import asyncio
from loguru import logger

from app.config.loader import AppConfig
from app.core.http_client import HttpClient
from app.core.proxy_manager import ExchangeProxyManager
from app.cache.redis_cache import RedisCache
from app.db.repository import AnnouncementRepository
from app.exchanges.factory import ExchangeFactory
from app.notifiers.telegram import TelegramNotifier
from app.notifiers.formatter import MessageFormatter
from app.notifiers.thread_mapper import ThreadMapper

from app.utils.tools import random_delay


class Orchestrator:
    """Main orchestrator with per-exchange configuration"""

    def __init__(self, config: AppConfig):
        self.config = config
        self._log = logger.bind(component="orchestrator")

    async def initialize_components(self):
        # Initialize components
        self._init_proxy_manager()
        await self._init_core_components()
        await self._init_scrapers()
        self._init_notifiers()

    def _init_proxy_manager(self):
        """Initialize proxy manager with per-exchange configs"""
        self.proxy_manager = ExchangeProxyManager()

        for name, exc_config in self.config.exchanges.items():
            if exc_config.enabled and exc_config.proxies:
                self.proxy_manager.register_exchange(name, exc_config.proxies)
                self._log.info(f"Registered {len(exc_config.proxies)} proxies for {name}")

    async def _init_core_components(self):
        """Initialize core components"""
        redis_cfg = self.config.general.get('redis', {})
        self.cache = RedisCache(
            redis_cfg.get('url', 'redis://localhost:6379'),
            redis_cfg.get('use_fake', True)
        )

        self.http = HttpClient(self.proxy_manager)
        self.formatter = MessageFormatter()

        exchanges = list(self.config.exchanges.keys())
        self.repo = AnnouncementRepository(
            self.config.general['db_path'],
            self.cache,
            exchanges
        )
        await self.repo.init()

    async def _init_scrapers(self):
        """Initialize exchange scrapers"""
        self.scrapers = []

        for name, exc_config in self.config.exchanges.items():
            if not exc_config.enabled:
                continue

            try:
                scraper = ExchangeFactory.create(
                    exc_config,
                    self.http,
                    self.repo
                )

                await scraper.initialize()

                self.scrapers.append(scraper)
                self._log.info(f"Initialized {name} scraper")
            except Exception as e:
                self._log.error(f"Failed to init {name}: {e}")

    def _init_notifiers(self):
        """Initialize notification system"""
        thread_mappings = self.config.telegram.thread_mappings
        default_thread = self.config.telegram.default_thread

        self.thread_mapper = ThreadMapper(thread_mappings, default_thread)
        self.notifier = TelegramNotifier(
            self.config.telegram.bot_token,
            self.config.telegram.chat_id
        )

    async def run(self):
        """Main run loop"""
        await self.initialize_components()
        self._log.info("System initialized")

        while True:
            try:
                await self._process_cycle()
            except Exception as e:
                self._log.error(f"Cycle error: {e}")

            await asyncio.sleep(self.config.general['poll_interval'])

    async def _process_cycle(self):
        """Process one polling cycle"""
        tasks = [self._process_exchange(scraper) for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        summary = []
        for scraper, result in zip(self.scrapers, results):
            if isinstance(result, Exception):
                summary.append(f"❌ {scraper.config.name}")
            else:
                new, total = result
                icon = "✅" if new > 0 else "✓"
                summary.append(f"{icon} {scraper.config.name} {new}/{total}")

        self._log.info(" | ".join(summary))

    async def _process_exchange(self, scraper):
        """Process single exchange"""
        try:
            announcements, total = await scraper.fetch_latest()

            await random_delay(scraper.config.delay)

            if not announcements:
                return 0, total

            # Save new announcements
            new_anns = await self.repo.insert_many_if_new(announcements)

            # Send notifications
            for ann in new_anns:
                thread_id = self.thread_mapper.get_thread_id(ann)
                message = self.formatter.format_telegram(ann)
                await self.notifier.send_with_thread(
                    ann.exchange,
                    message,
                    thread_id
                )

            return len(new_anns), total

        except Exception as e:
            self._log.error(f"Exchange error: {e}", exchange=scraper.config.name)
            raise

    async def cleanup(self):
        """Cleanup resources"""
        await self.http.close()
        await self.notifier.close()
        await self.cache.close()
