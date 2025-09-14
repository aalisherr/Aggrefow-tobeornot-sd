from typing import Dict, Any, List

from app.modules.parsers.exchanges.base import ExchangeScraper


class BitgetScraper(ExchangeScraper):
    """Bitget scraper with category-based classification"""

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and "pageProps" in raw_data:
            list_data = raw_data.get("pageProps", {}).get("list", {})
            items = list_data.get("latestArticles", [])

            self._log.debug(f"Extracted {len(items)} items from Bitget API")
            return items

        self._log.error(f"Failed to parse Bitget API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        return item.get('sectionName', '')

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get('contentId', ''))

    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')

    def extract_body(self, item: Dict) -> str:
        # Bitget doesn't provide body in list view, return title as fallback
        return item.get('title', '')

    def extract_timestamp(self, item: Dict) -> int:
        # showTime is in milliseconds
        timestamp = item.get('showTime')
        if timestamp:
            return int(timestamp) // 1000  # Convert to seconds
        return 0

    def build_url(self, item: Dict) -> str:
        # Bitget provides jumpUrl directly
        url = item.get('jumpUrl')
        if url:
            return url

        # Fallback: construct URL from contentId
        content_id = self.extract_source_id(item)
        return f"https://www.bitgetapps.com/en/support/articles/{content_id}" if content_id else "https://www.bitget.com/support"
