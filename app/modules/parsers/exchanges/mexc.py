from typing import Dict, Any, List
from app.modules.parsers.exchanges.base import ExchangeScraper


class MexcScraper(ExchangeScraper):
    """MEXC scraper with category-based classification"""

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and raw_data.get("code") == 0:
            data = raw_data.get("data", {})
            items = data.get("result", [])

            return items

        self._log.error(f"Failed to parse MEXC API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str | None:
        return str(item.get('sectionId'))
        # return
        # title = item.get('title', '').lower()
        #
        # # Check title with regex patterns
        # for announcement_type, patterns in __CLASSIFY_PATTERNS__.items():
        #     for pattern in patterns:
        #         if re.search(pattern, title):
        #             return announcement_type

    def extract_source_id(self, item: Dict) -> str:
        return str(item.get('id', ''))

    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')

    def extract_body(self, item: Dict) -> str:
        # MEXC API doesn't provide body in the list response
        return item.get('description', '') + item.get('content', '')

    def extract_timestamp(self, item: Dict) -> int:
        return item.get('displayTime', 0)

    def build_url(self, item: Dict) -> str:
        article_endpoint = item.get('enPath', '')

        return f"{self._base_url}/announcements/article/{article_endpoint}"
