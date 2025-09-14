import asyncio
from loguru import logger
from typing import Dict

from app.db.config.loader import AppConfig
from app.core.http_client import HttpClient
from app.core.proxy_manager import ExchangeProxyManager
from app.db.cache.redis_cache import RedisCache
from app.db.repository import AnnouncementRepository
from app.modules.parsers.exchanges.factory import ExchangeFactory
from app.notifiers.telegram import TelegramNotifier
from app.notifiers.formatter import MessageFormatter
from app.notifiers.thread_mapper import ThreadMapper
from app.utils.tools import random_delay


class Orchestrator:
    """Orchestrator with independent exchange loops for maximum speed"""

    def __init__(self, config: AppConfig):
        self.config = config
        self._log = logger.bind(component="orchestrator")
        self._exchange_tasks: Dict[str, asyncio.Task] = {}
        self._running = True
        self._stats = {}  # Track exchange statistics

    async def initialize_components(self):
        """Initialize all components"""
        self._init_proxy_manager()
        await self._init_core_components()
        await self._init_scrapers()
        self._init_notifiers()

    def _init_proxy_manager(self):
        """Initialize proxy manager with per-exchange configs"""
        self.proxy_manager = ExchangeProxyManager()
        self.proxy_manager.register_from_config(self.config.exchanges)

        log_msg = ""
        for name, exc_config in self.config.exchanges.items():
            if exc_config.enabled and exc_config.proxies:
                log_msg += f"{name.capitalize()} ({len(exc_config.proxies)}) | "

        self._log.info(f"Registered exchanges proxies: {log_msg}")

    async def _init_core_components(self):
        """Initialize core components"""
        redis_cfg = self.config.general.get('redis', {})
        self.cache = RedisCache(
            redis_cfg.get('url', 'redis://localhost:6379'),
            redis_cfg.get('use_fake', True)
        )

        self.formatter = MessageFormatter()
        exchanges = list(self.config.exchanges.keys())

        self.repo = AnnouncementRepository(
            self.config.general['db_path'],
            self.cache,
            exchanges
        )
        await self.repo.init()

    async def _init_scrapers(self):
        """Initialize exchange scrapers with isolated HTTP clients"""
        self.scrapers = {}
        self.http_clients = []

        for name, exc_config in self.config.exchanges.items():
            if not exc_config.enabled:
                continue

            try:
                # Create dedicated HTTP client for this exchange
                exchange_http = HttpClient(self.proxy_manager, name)
                self.http_clients.append(exchange_http)

                # Setup exchange-specific session
                await self._setup_exchange_session(exchange_http, exc_config)

                scraper = ExchangeFactory.create(
                    exc_config,
                    exchange_http,
                    self.repo
                )
                await scraper.initialize()

                self.scrapers[name] = {
                    'scraper': scraper,
                    'poll_interval': exc_config.monitoring.poll_interval,
                    'http_client': exchange_http
                }

                # Initialize stats
                self._stats[name] = {
                    'success': 0,
                    'errors': 0,
                    'total': 0,
                    'total_per_check': 0
                }

                # self._log.info(
                #     f"Initialized {name} with {exc_config.poll_interval or self.config.general['poll_interval']}s interval")

            except Exception as e:
                self._log.error(f"Failed to init {name}: {e}")

    async def _setup_exchange_session(self, http_client: HttpClient, exc_config):
        """Setup exchange-specific session configuration"""
        if exc_config.headers:
            http_client.session.headers.update(exc_config.headers)

        if exc_config.proxies:
            proxy = exc_config.proxies[0]
            http_client.session.proxies.update({"http": proxy, "https": proxy})

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
        """Main run loop - starts independent exchange loops"""
        await self.initialize_components()
        self._log.info("System initialized, starting independent exchange loops")

        # Start independent loop for each exchange
        for name, scraper_data in self.scrapers.items():
            task = asyncio.create_task(
                self._exchange_loop(name, scraper_data),
                name=f"exchange_{name}"
            )
            self._exchange_tasks[name] = task

        # Start stats reporter
        stats_task = asyncio.create_task(self._stats_reporter())

        try:
            # Wait for all tasks (they should run forever)
            await asyncio.gather(
                *self._exchange_tasks.values(),
                stats_task,
                return_exceptions=True
            )
        except KeyboardInterrupt:
            self._log.info("Shutting down...")
            self._running = False

    async def _exchange_loop(self, name: str, scraper_data: dict):
        """Independent loop for a single exchange"""
        scraper = scraper_data['scraper']
        poll_interval = scraper_data['poll_interval']

        self._log.info(f"Starting {name} loop with {poll_interval}s interval")

        while self._running:
            try:
                # Process this exchange
                start_time = asyncio.get_event_loop().time()
                new_count, total_per_check = await self._process_exchange(scraper)
                process_time = asyncio.get_event_loop().time() - start_time
                # print(new_count, total, process_time)
                # Update stats
                self._stats[name]['total'] += 1
                self._stats[name]['success'] += new_count
                self._stats[name]['total_per_check'] = total_per_check

                log_msg = f"{name}: {new_count} / {total_per_check} / {process_time:.2f}s"
                if new_count > 0:
                    self._log.info(f"✅{log_msg}")
                else:
                    self._log.debug(f"{log_msg}")

            except Exception as e:
                self._stats[name]['errors'] += 1
                self._log.error(f"❌ {name} error: {e}")

            # Wait for next cycle (specific to this exchange)
            await random_delay(scraper.poll_interval)

    async def _process_exchange(self, scraper):
        """Process single exchange"""
        announcements, total = await scraper.fetch_latest()
        if not announcements:
            return 0, total

        # Save and notify for new announcements
        new_anns = await self.repo.insert_many_if_new(announcements)

        for ann in new_anns[:5]:  # optimization for testing
            thread_id = self.thread_mapper.get_thread_id(ann)
            message = self.formatter.format_telegram(ann)
            # print(message)
            await self.notifier.send_with_thread(
                ann.exchange,
                message,
                thread_id
            )

        return len(new_anns), total

    async def _stats_reporter(self):
        """Periodically report statistics"""
        report_interval = 60  # Report every minute

        while self._running:
            await asyncio.sleep(report_interval)

            summary = []
            for name, stats in self._stats.items():

                status = f"📊{name.capitalize()}: [{stats['success']} / {stats['total_per_check']} / {stats['total']}]"
                if stats['errors'] > 0:
                    status += f", {stats['errors']} errors"

                summary.append(status)

                stats['success'] = 0
                stats['total'] = 0
                stats['errors'] = 0

            self._log.info(" | ".join(summary))

    async def cleanup(self):
        """Cleanup resources"""
        self._running = False

        # Cancel all exchange tasks
        for name, task in self._exchange_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                self._log.debug(f"Cancelled {name} task")

        # Close HTTP clients
        for http_client in self.http_clients:
            await http_client.close()

        await self.notifier.close()
        await self.cache.close()

        self._log.info("Cleanup complete")
