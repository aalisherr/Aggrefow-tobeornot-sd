from typing import Dict, Type
from app.config.loader import ExchangeConfig
from app.exchanges.base import ExchangeScraper
from app.exchanges.binance import BinanceScraper
from app.exchanges.bingx import BingXScraper
from app.exchanges.bitget import BitgetScraper
from app.exchanges.bithumb import BithumbScraper
from app.exchanges.bybit import BybitScraper
from app.exchanges.gate import GateScraper
from app.exchanges.kucoin import KuCoinScraper
from app.exchanges.mexc import MexcScraper
from app.exchanges.okx import OkxScraper
from app.exchanges.upbit import UpbitScraper


class ExchangeFactory:
    """Factory for creating exchange scrapers"""

    _registry: Dict[str, Type[ExchangeScraper]] = {
        # 'binance': BinanceScraper,
        # 'bybit': BybitScraper,
        # 'kucoin': KuCoinScraper,
        # 'okx': OkxScraper,
        # 'mexc': MexcScraper,
        # 'gate': GateScraper,
        # 'bitget': BitgetScraper,
        # "bingx": BingXScraper,
        # "upbit": UpbitScraper,
        "bithumb": BithumbScraper,
    }

    @classmethod
    def create(
            cls,
            config: ExchangeConfig,
            http_client,
            repository
    ) -> ExchangeScraper:
        """Create scraper for exchange"""
        scraper_class = cls._registry.get(config.name.lower())
        if not scraper_class:
            raise ValueError(f"Unknown exchange: {config.name}")

        return scraper_class(config, http_client, repository)

    @classmethod
    def register(cls, name: str, scraper_class: Type[ExchangeScraper]):
        """Register new exchange scraper"""
        cls._registry[name.lower()] = scraper_class