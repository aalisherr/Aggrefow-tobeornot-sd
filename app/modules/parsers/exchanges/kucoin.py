from typing import Dict, Any, List
from app.modules.parsers.exchanges.base import ExchangeScraper


class KuCoinScraper(ExchangeScraper):
    """KuCoin scraper with category-based classification"""
    
    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and raw_data.get('success'):
            items = raw_data.get('items', [])
            return items
        return []
    
    async def extract_category(self, item: Dict) -> str:
        categories = item.get('categories', [])
        categories.sort(key=lambda x: x.get('id', '') != 26, reverse=True)  # send to end latest announcements
        if first_category := categories[0] if categories else {}:
            return first_category.get('name', '')
        return ''
    
    def extract_source_id(self, item: Dict) -> str:
        return str(item.get('id', ''))
    
    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')
    
    def extract_body(self, item: Dict) -> str:
        return self.strip_html(item.get('content', ''))
    
    def extract_timestamp(self, item: Dict) -> int:
        return item.get('publish_ts', 0) * 1000
    
    def build_url(self, item: Dict) -> str:
        path = item.get('path', '')
        return f"{self._base_url}/announcement{path}"