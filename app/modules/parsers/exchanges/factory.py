from typing import Dict, Type
from app.db.config.loader import ExchangeConfig
from . import BybitScraper, BinanceScraper, KuCoinScraper, OkxScraper, MexcScraper, GateScraper, BitgetScraper, \
    BingXScraper, UpbitScraper, BithumbScraper, ExchangeScraper, HyperLiquidScraper


class ExchangeFactory:
    """Factory for creating exchange scrapers"""

    _registry: Dict[str, Type[ExchangeScraper]] = {
        'binance': BinanceScraper,
        # 'bybit': BybitScraper,
        # 'kucoin': KuCoinScraper,
        # 'okx': OkxScraper,
        # 'mexc': MexcScraper,
        # 'gate': GateScraper,
        # 'bitget': BitgetScraper,
        # "bingx": BingXScraper,
        # "upbit": UpbitScraper,
        # "bithumb": BithumbScraper,
        # 'hyperliquid': HyperLiquidScraper,
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