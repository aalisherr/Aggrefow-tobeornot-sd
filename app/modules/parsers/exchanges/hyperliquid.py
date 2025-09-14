from typing import Dict, Any, List
from app.modules.parsers.exchanges.base import ExchangeScraper


class HyperLiquidScraper(ExchangeScraper):
    """Hyperliquid scraper with category-based classification"""

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict):
            items = raw_data.get('entries', [])
            return items
        return []

    async def extract_category(self, item: Dict) -> str:
        return item.get("category", "")

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get("uuid", ""))

    def extract_title(self, item: Dict) -> str:
        return item.get("title", "")

    def extract_body(self, item: Dict) -> str:
        return item.get("preview", "")

    def extract_timestamp(self, item: Dict) -> int:
        return self.convert_date_to_timestamp(item['createdAt'])

    def build_url(self, item: Dict) -> str:
        url_path = f"https://app.hyperliquid.xyz/trade/"

        tickers = self.extract_tickers(item.get("title"))
        if not tickers:
            return url_path
        return f"{url_path}{tickers[0]}"