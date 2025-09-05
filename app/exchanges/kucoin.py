from typing import Dict, Any, List, Optional
from app.exchanges.base import ExchangeScraper


class KuCoinScraper(ExchangeScraper):
    """KuCoin scraper with category-based classification"""
    
    async def fetch_raw_data(self, proxy: Optional[str] = None) -> Any:
        params = {'page': '1', 'pageSize': '1'}
        kwargs = {'params': params}
        if proxy:
            kwargs['proxy'] = proxy
        
        return await self.http.get(self.url, **kwargs)
    
    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and raw_data.get('success'):
            items = raw_data.get('items', [])
            return items
        return []
    
    async def extract_category(self, item: Dict) -> str:
        categories = item.get('categories', [])
        if categories and isinstance(categories[0], dict):
            return categories[0].get('name', '')
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
        return f"{self.config.base_url}/announcement{path}"