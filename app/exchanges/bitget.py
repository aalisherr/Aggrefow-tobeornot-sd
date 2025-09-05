import re
from typing import Dict, Any, List, Optional

from app.exchanges.base import ExchangeScraper
from app.models.announcement import AnnouncementType

CATEGORY_DICT = {
    "Latest news": ["Announcements", "Bitget news"],
    "New listings": ["New listings", "Spot", "Futures", "Margin", "Copy Trading", "Bots"],
    "Competitions and promotions": [
        "Competitions and promotions",
        "Ongoing competitions and promotions",
        "Previous competitions & events",
        "Reward Distribution",
        "KCGI",
        "VIP campaigns"
    ],
    "Product updates": [
        "Product updates",
        "Unified trading account",
        "Spot",
        "Futures",
        "Margin",
        "Copy trading",
        "Bots",
        "Earn",
        "Crypto Loan",
        "Bitget Swap"
    ],
    "Security": ["Security", "Security Information"],
    "API trading": ["API trading", "API Announcement"],
    "Delisting information": ["Delisting information", "Trading pair delisting"],
    "Fiat": [
        "Fiat",
        "Credit/debit card",
        "P2P trading",
        "Bank deposit",
        "Cash conversion",
        "Third-party"
    ],
    "Maintenance or system updates": [
        "Maintenance or system updates",
        "Asset maintenance",
        "Spot Maintenance",
        "System Updates",
        "Futures Maintenance"
    ],
    "Other": ["Other"]
}


class BitgetScraper(ExchangeScraper):
    """Bitget scraper with category-based classification"""

    async def fetch_raw_data(self) -> Any:
        return await self.http.get(
            self.url
        )

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and "pageProps" in raw_data:
            list_data = raw_data.get("pageProps", {}).get("list", {})
            items = list_data.get("latestArticles", [])

            self._log.debug(f"Extracted {len(items)} items from Bitget API")
            return items

        self._log.error(f"Failed to parse Bitget API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        section_name = item.get('sectionName', '')

        # Direct match first
        for category_name, section_names in CATEGORY_DICT.items():
            if section_name in section_names:
                return category_name

        self._log.warning(f"Unknown category: {section_name}")
        return AnnouncementType.OTHER

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
