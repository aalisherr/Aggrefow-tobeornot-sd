from typing import Dict, Any, List
from app.modules.parsers.exchanges.base import ExchangeScraper


class BybitScraper(ExchangeScraper):
    """Bybit scraper with category-based classification"""

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and "result" in raw_data:
            items = raw_data.get("result", {}).get("hits", [])
            # items = self.change_items_key(items, "publish_time", "publish_ts")
            return items  # [h for h in hits if not h.get("is_top")]  # Skip pinned
        return []

    async def extract_category(self, item: Dict) -> str:
        return (item.get("category") or {}).get("title", "")

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get("objectID", ""))

    def extract_title(self, item: Dict) -> str:
        return item.get("title", "")

    def extract_body(self, item: Dict) -> str:
        return item.get("description", "")

    def extract_timestamp(self, item: Dict) -> int:
        return int(item.get("date_timestamp", 0)) * 1000

    def build_url(self, item: Dict) -> str:
        url_path = item.get("url", "")
        if url_path.startswith("/"):
            return f"{self._base_url}{url_path}"
        return url_path