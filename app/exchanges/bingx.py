from typing import Dict, Any, List, Optional
from datetime import datetime

from app.exchanges.base import ExchangeScraper
from app.models.announcement import AnnouncementType


CATEGORY_DICT = {
    "Latest Announcements": [360004917494],
    "Latest Promotions": [11257060320143],
    "Product Updates": [11256997796495],
    "Asset Maintenance": [11257016265487],
    "System Maintenance": [11523620946319],
    "Spot Listing": [11257060005007],
    "Futures Listing": [11257015822991],
    "Innovation Listing": [13117025062927],
    "Funding Rate": [11257028004239],
    "Delisting": [11257015847311],
    "Crypto Scout": [11257028024847]
}


class BingXScraper(ExchangeScraper):
    """BingX scraper with category-based classification"""

    async def fetch_raw_announcements(self, proxy: Optional[str] = None) -> Any:
        headers = {
            'app_version': '5.1.15',
            'device_id': 'b7ccd3a2b10a4c0c819898c3c5c013d6',
            'lang': 'en',
            'platformid': '30',
            'sign': '3481E4581CE30D632A69CD70D795B83A7F04149A6EFF7FEA2EF7E637D9747B5E',
            'timestamp': '1756979032336',
            'timezone': '3',
            'traceid': '7322b05aab2048c6ad6895b1c735345a',
        }

        params = {
            'sectionId': '360004917494',
            'page': '1',
            'pageSize': '20',
        }
        kwargs = {'params': params}
        if proxy:
            kwargs['proxy'] = proxy

        return await self.http.get(
            self.url,
            **kwargs,
            headers=headers
        )

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and raw_data.get("code") == 0:
            data = raw_data.get("data", {})
            items = data.get("result", [])

            self._log.debug(f"Extracted {len(items)} items from BingX API")
            return items

        self._log.error(f"Failed to parse BingX API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        section_id = item.get('sectionId') or item.get('newSectionId')

        if section_id is not None:
            for category_name, section_ids in CATEGORY_DICT.items():
                if section_id in section_ids:
                    return category_name

        self._log.warning(f"Unknown section ID: {section_id}")
        return AnnouncementType.OTHER

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get('articleId') or item.get('newArticleId', ''))

    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')

    def extract_body(self, item: Dict) -> str:
        # BingX doesn't provide body in list view, return title as fallback
        return item.get('title', '')

    def extract_timestamp(self, item: Dict) -> int:
        # Parse ISO format timestamp
        create_time = item.get('createTime')
        if create_time:
            try:
                # Remove timezone info and parse
                dt_str = create_time.replace('+08:00', '')
                dt = datetime.fromisoformat(dt_str)
                return int(dt.timestamp())
            except Exception as e:
                self._log.warning(f"Failed to parse timestamp {create_time}: {e}")
        return 0

    def build_url(self, item: Dict) -> str:
        # Construct URL from article ID
        article_id = self.extract_source_id(item)
        return f"https://bingx.com/en/support/articles/{article_id}" if article_id else "https://bingx.com/support"