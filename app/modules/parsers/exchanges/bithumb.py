from typing import Dict, Any, List
from datetime import datetime

from app.modules.parsers.exchanges.base import ExchangeScraper


class BithumbScraper(ExchangeScraper):
    """Bithumb scraper with category-based classification"""

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and "pageProps" in raw_data:
            page_props = raw_data.get("pageProps", {})
            items = page_props.get("noticeList", [])

            self._log.debug(f"Extracted {len(items)} items from Bithumb API")
            return items

        self._log.error(f"Failed to parse Bithumb API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        """Extract and map category using new config structure"""
        return item.get('categoryName1', '')

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get('id', ''))

    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')

    def extract_body(self, item: Dict) -> str:
        # Bithumb doesn't provide body in list view, return title as fallback
        return item.get('title', '')

    def extract_timestamp(self, item: Dict) -> int:
        # Parse datetime format: "2025-09-03 09:14:28"
        pub_datetime = item.get('publicationDateTime')
        if pub_datetime:
            try:
                dt = datetime.strptime(pub_datetime, '%Y-%m-%d %H:%M:%S')
                return int(dt.timestamp() * 1000)
            except Exception as e:
                self._log.warning(f"Failed to parse timestamp {pub_datetime}: {e}")
        return 0

    def build_url(self, item: Dict) -> str:
        # Construct URL from notice ID
        notice_id = self.extract_source_id(item)
        base_url = self._base_url
        return f"{base_url}/notice/{notice_id}" if notice_id else f"{base_url}/notice"