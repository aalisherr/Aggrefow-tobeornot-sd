import re
from typing import Dict, Any, List, Optional

from app.exchanges.base import ExchangeScraper
from app.models.announcement import AnnouncementType

CATEGORY_DICT = {
    "Announcements": [0],
    "Activities": [11, 32, 33, 34, 35, 36, 69],
    "Brand Milestones": [29],
    "Alpha": [28],
    "Bi-Weekly Reports": [3],
    "Gate Research": [5],
    "Gate Charity": [9],
    "Gate Wallet": [30],
    "New Crypto Listings": [7, 61, 38, 37, 39, 40],
    "Delistings": [15],
    "VIP Services": [65],
    "Institutional Services": [66, 68, 67],
    "Earn": [10, 62, 43, 44, 45, 46, 47, 48, 49, 50],
    "Options": [31],
    "Gate Live": [12],
    "GT": [25],
    "Fees & Precision": [53, 55, 54],
    "API Updates": [27],
    "Maintenance / _ Updates": [56, 57, 58, 59, 60],
    "Other": [1]
}


class GateScraper(ExchangeScraper):
    """Gate.io scraper with category-based classification"""

    async def fetch_raw_announcements(self, proxy: Optional[str] = None) -> Any:
        params = {
            'category': 'lastest',
        }
        kwargs = {'params': params}
        if proxy:
            kwargs['proxy'] = proxy

        return await self.http.get(
            self.url,
            **kwargs
        )

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and "pageProps" in raw_data:
            list_data = raw_data.get("pageProps", {}).get("listData", {})
            items = list_data.get("list", [])

            self._log.debug(f"Extracted {len(items)} items from Gate.io API")
            return items

        self._log.error(f"Failed to parse Gate.io API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        cate_id = item.get('cate_id')
        if cate_id is not None:
            for category_name, cate_ids in CATEGORY_DICT.items():
                if cate_id in cate_ids:
                    return category_name

        self._log.warning(f"Unknown category ID: {cate_id}")
        return AnnouncementType.OTHER

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