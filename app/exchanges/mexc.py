import re
from typing import Dict, Any, List, Optional
from app.exchanges.base import ExchangeScraper
from app.models.announcement import AnnouncementType

# Fast cached variant of classify_by_category
__CLASSIFY_PATTERNS__ = {
    "New listings": [
        r'^\[initial listing\]',
        r'^\[initial futures listing\]',
        r'^mexc pre-market trading',
    ],
    "Delistings": [
        r'^delisting of',
    ]
}


class MexcScraper(ExchangeScraper):
    """MEXC scraper with category-based classification"""

    async def fetch_raw_announcements(self, proxy: Optional[str] = None) -> Any:
        params = {
            'page': '1',
            'perPage': '3',  # Fetch more items per request
        }
        kwargs = {'params': params}
        if proxy:
            kwargs['proxy'] = proxy

        return await self.http.get(
            self.url,
            **kwargs
        )

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and raw_data.get("code") == 0:
            data = raw_data.get("data", {})
            items = data.get("results", [])

            # Convert timestamps to the expected format
            for item in items:
                # Convert ISO format to timestamp
                if created_at := item.get('createdAt'):
                    item['timestamp'] = self.convert_date_to_timestamp(created_at)
                else:
                    item['timestamp'] = 0

            return items

        self._log.error(f"Failed to parse MEXC API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        title = item.get('title', '').lower()

        # Check title with regex patterns
        for announcement_type, patterns in __CLASSIFY_PATTERNS__.items():
            for pattern in patterns:
                if re.search(pattern, title):
                    return announcement_type

        # Check parent sections for category information
        parent_sections = item.get('parentSections', [])
        if parent_sections:
            section_name = parent_sections[0].get('name', '').lower()
            return section_name

        return AnnouncementType.OTHER

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get('id', ''))

    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')

    def extract_body(self, item: Dict) -> str:
        # MEXC API doesn't provide body in the list response
        return ""

    def extract_timestamp(self, item: Dict) -> int:
        return item.get('timestamp', 0)

    def build_url(self, item: Dict) -> str:
        article_id = self.extract_source_id(item)

        return f"https://www.mexc.com/support/articles/{article_id}"
