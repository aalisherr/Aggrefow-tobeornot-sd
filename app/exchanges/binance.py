from typing import Dict, Any, List, Optional
from app.exchanges.base import ExchangeScraper


class BinanceScraper(ExchangeScraper):
    """Binance scraper with category-based classification"""

    async def fetch_raw_data(self, proxy: Optional[str] = None) -> Any:
        params = {
            'type': '1',
            'pageNo': '1',
            'pageSize': '1',
        }
        kwargs = {'params': params}
        if proxy:
            kwargs['proxy'] = proxy

        return await self.http.get(self.url, **kwargs)

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and "data" in raw_data:
            items = []
            catalogs = raw_data.get("data", {}).get("catalogs", [])

            for catalog in catalogs:
                catalog_name = catalog.get("catalogName", "")
                for article in catalog.get("articles", []):
                    article["category"] = catalog_name
                    items.append(article)

            return items
        return []

    async def extract_category(self, item: Dict) -> str:
        return item.get("category", "")

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get("id") or item.get("code", ""))

    def extract_title(self, item: Dict) -> str:
        return self.strip_html(item.get("title", ""))

    def extract_body(self, item: Dict) -> str:
        return self.strip_html(item.get("body", ""))

    def extract_timestamp(self, item: Dict) -> int:
        return int(item.get("releaseDate", 0))

    def build_url(self, item: Dict) -> str:
        if code := item.get("code"):
            return f"{self.config.base_url}/en/support/announcement/{code}"
        return f"{self.config.base_url}/en/support/announcement"
