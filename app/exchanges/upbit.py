from typing import Dict, Any, List, Optional
from datetime import datetime

from app.exchanges.base import ExchangeScraper
from app.models.announcement import AnnouncementType


class UpbitScraper(ExchangeScraper):
    """Upbit scraper with direct category classification"""

    async def fetch_raw_announcements(self, proxy: Optional[str] = None) -> Any:
        params = {
            'os': 'web',
            'page': '1',
            'per_page': '5',
            'category': 'all',
        }
        kwargs = {'params': params}
        if proxy:
            kwargs['proxy'] = proxy

        return await self.http.get(
            self.url,
            **kwargs
        )

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and raw_data.get("success"):
            data = raw_data.get("data", {})
            items = data.get("notices", [])

            self._log.debug(f"Extracted {len(items)} items from Upbit API")
            return items

        self._log.error(f"Failed to parse Upbit API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        category = item.get('category', '')
        return category if category else AnnouncementType.OTHER

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get('id', ''))

    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')

    def extract_body(self, item: Dict) -> str:
        # Upbit doesn't provide body in list view, return title as fallback
        return item.get('title', '')

    def extract_timestamp(self, item: Dict) -> int:
        # Parse ISO format timestamp
        listed_at = item.get('listed_at')
        if listed_at:
            try:
                dt = datetime.fromisoformat(listed_at.replace('+09:00', '+09:00'))
                return int(dt.timestamp())
            except Exception as e:
                self._log.warning(f"Failed to parse timestamp {listed_at}: {e}")
        return 0

    def build_url(self, item: Dict) -> str:
        # Construct URL from notice ID
        notice_id = self.extract_source_id(item)
        return f"https://upbit.com/service_center/notice?id={notice_id}" if notice_id else "https://upbit.com/service_center/notice"