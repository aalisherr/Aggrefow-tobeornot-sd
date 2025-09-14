from typing import Dict, Any, List
from datetime import datetime

from app.modules.parsers.exchanges.base import ExchangeScraper
from app.modules.parsers.generators.bingx_headers.bingx_headers import BingxHeaderGenerator


class BingXScraper(ExchangeScraper):
    """BingX scraper with category-based classification"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def initialize_headers(self):
        generator = BingxHeaderGenerator()
        headers = generator.generate_headers(**self.kwargs)

        self.http.session.headers.update(headers)

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and raw_data.get("code") == 0:
            data = raw_data.get("data", {})
            items = data.get("result", [])

            self._log.debug(f"Extracted {len(items)} items from BingX API")
            return items

        self._log.error(f"Failed to parse BingX API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        return item.get('sectionId') or item.get('newSectionId')

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