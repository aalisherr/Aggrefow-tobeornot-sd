import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.exchanges.base import ExchangeScraper
from app.models.announcement import AnnouncementType

CATEGORY_DICT = {
    "Transaction Caution": ["거래유의"],
    "Delisting": ["거래지원종료"],
    "Public Notice / Disclosure": ["공시"],
    "Market Addition": ["마켓 추가"],
    "New Service": ["신규서비스"],
    "Notice / Guide": ["안내"],
    "Update": ["업데이트"],
    "Event": ["이벤트"],
    "Deposits & Withdrawals": ["입출금"],
    "Maintenance / Inspection": ["점검"]
}


class BithumbScraper(ExchangeScraper):
    """Bithumb scraper with category-based classification"""

    async def fetch_raw_data(self, proxy: Optional[str] = None) -> Any:
        params = {
            'category': '',
            'page': '1',
        }
        kwargs = {
            'params': params
        }
        if proxy:
            kwargs['proxy'] = proxy

        return await self.http.get(
            self.url,
            **kwargs
        )

    def extract_items(self, raw_data: Any) -> List[Dict]:
        if isinstance(raw_data, dict) and "pageProps" in raw_data:
            page_props = raw_data.get("pageProps", {})
            items = page_props.get("noticeList", [])

            self._log.debug(f"Extracted {len(items)} items from Bithumb API")
            return items

        self._log.error(f"Failed to parse Bithumb API response: {raw_data}")
        return []

    async def extract_category(self, item: Dict) -> str:
        category_name = item.get('categoryName1', '')

        # Direct match first
        for category_name_en, category_names_kr in CATEGORY_DICT.items():
            if category_name in category_names_kr:
                return category_name_en

        # Partial match fallback
        for category_name_en, category_names_kr in CATEGORY_DICT.items():
            for kr_name in category_names_kr:
                if kr_name in category_name or category_name in kr_name:
                    return category_name_en

        self._log.warning(f"Unknown category: {category_name}")
        return AnnouncementType.OTHER

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
                return int(dt.timestamp())
            except Exception as e:
                self._log.warning(f"Failed to parse timestamp {pub_datetime}: {e}")
        return 0

    def build_url(self, item: Dict) -> str:
        # Construct URL from notice ID
        notice_id = self.extract_source_id(item)
        return f"{self.config.base_url}/notice/{notice_id}" if notice_id else f"{self.config.base_url}/notice"

    def get_headers(self):
        headers = self.http.DEFAULT_HEADERS
        return {
            **headers,
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9,uk;q=0.8,ru;q=0.7,en-GB;q=0.6,pl;q=0.5,ko;q=0.4',
            'priority': 'u=1, i',
            'referer': 'https://feed.bithumb.com/',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
        }
