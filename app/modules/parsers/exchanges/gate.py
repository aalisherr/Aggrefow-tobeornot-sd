from typing import Dict, Any, List

from app.modules.parsers.exchanges.base import ExchangeScraper


class GateScraper(ExchangeScraper):
    """Gate.io scraper with category-based classification"""

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and "pageProps" in raw_data:
            list_data = raw_data.get("pageProps", {}).get("listData", {})
            items = list_data.get("list", [])
            self._log.debug(f"Extracted {len(items)} items from Gate.io API")
            return items

        self._log.error(f"Failed to parse Gate.io API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        return str(item.get('cate_id'))

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get('id', ''))

    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')

    def extract_body(self, item: Dict) -> str:
        return item.get('brief', '')

    def extract_timestamp(self, item: Dict) -> int:
        # Gate.io provides timestamp in release_timestamp field
        timestamp = item.get('release_timestamp') or item.get('created_t', 0)
        return int(timestamp) if timestamp else 0

    def build_url(self, item: Dict) -> str:
        # Gate.io provides the URL directly
        url = item.get('url')
        if url:
            return url

        # Fallback: construct URL from article ID
        article_id = self.extract_source_id(item)
        return f"https://www.gate.com/article/{article_id}" if article_id else "https://www.gate.com/announcements"

    def get_headers(self):
        return {
            "User-Agent": "python-requests/2.32.5"
        }