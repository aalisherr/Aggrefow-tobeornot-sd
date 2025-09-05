import re
import json
import traceback

from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from app.exchanges.base import ExchangeScraper
from app.models.announcement import AnnouncementType


# Fast cached variant of classify_by_category
__CLASSIFY_PATTERNS__ = {
    "New listings": [
        r'list.*for spot trading',
        r'list.*pre-market',
        r'to list \w+',
        r'listing of \w+',
        r'support.*migration',
        r'enable.*Simple Earn.*for \w+',
        r'list.*crypto$',
        r'will list.*\(',
        r'add.*trading pair',
        r'launch.*trading',
    # ],
    # "New listings": [
        r'list.*perpetual futures',
        r'enable margin trading.*for \w+'
    ],
    "Delistings": [
        r'OKX to delist \w+'
    ]
}


class OkxScraper(ExchangeScraper):
    """OKX scraper with category-based classification"""

    async def fetch_raw_data(self, proxy: Optional[str] = None) -> Any:
        kwargs = {}
        if proxy:
            kwargs['proxy'] = proxy
        #
        # return """
        #         <script data-id="app_data_for_ssr" type="application/json" id="appState">
        #             {
        #                 "appContext": {
        #                     "initialProps": {
        #                         "supportBanner": {
        #                             "text": ""
        #                         },
        #                         "sectionData": {
        #                             "articleList": {
        #                                 "sys": {
        #                                     "type": "Array"
        #                                 },
        #                                 "total": 2315,
        #                                 "skip": 0,
        #                                 "limit": 15,
        #                                 "items": [
        #                                     {
        #                                         "id": "2OvDhPlU2zYSzowfVR6xAYO",
        #                                         "slug": "okx-to-list-usd1-world-liberty-financial-usd-for-spot-trading",
        #                                         "title": "OKX to list USD1 (World Liberty Financial USD) for spot trading",
        #                                         "createdAt": "2027-12-28T06:18:03.869Z",
        #                                         "updatedAt": "2026-12-01T12:33:41.185Z",
        #                                         "publishTime": "2027-12-29T14:21+08:00"
        #                                     }
        #                                 ]
        #                             }
        #                         }
        #                     }
        #                 }
        #             }
        #             </script>"""
        return await self.http.request("GET", self.url, **kwargs)

    def extract_items(self, raw_data: Any) -> List[Dict]:
        try:
            soup = BeautifulSoup(raw_data, 'html.parser')
            script_tag = soup.find('script', {'id': 'appState'})

            if not script_tag:
                self._log.error("Could not find appState script tag")
                return []

            json_data = json.loads(script_tag.string)
            items = (json_data.get('appContext', {})
                     .get('initialProps', {})
                     .get('sectionData', {})
                     .get('articleList', {})
                     .get('items', []))

            for item in items:
                item['publishTime'] = self.convert_date_to_timestamp(item['publishTime'])

            return items

        except (json.JSONDecodeError, AttributeError) as e:
            self._log.error(f"Failed to parse OKX HTML data: {e}")
            return []

    async def extract_category(self, item: Dict) -> str:
        title = item.get('title', '').lower()

        # First: check title with regex patterns
        for announcement_type, patterns in __CLASSIFY_PATTERNS__.items():
            for pattern in patterns:
                if re.search(pattern, title):
                    return announcement_type

        # Second: if not found, fetch article page to get section title
        slug = item.get('slug', '')

        if slug:
            try:
                article_url = f"https://www.okx.com/help/{slug}"
                response = await self.http.request("GET", article_url)  # Assuming sync method exists

                soup = BeautifulSoup(response, 'html.parser')
                script_tag = soup.find('script', {'data-id': '__app_data_for_ssr__'})

                if script_tag and script_tag.string:
                    json_data = json.loads(script_tag.string.strip())

                    section_title = (json_data
                                     .get('appContext', {})
                                     .get('serverSideProps', {})
                                     .get('currentPost', {})
                                     .get('section', {})
                                     .get('title', '')).lower()

                    return section_title
            except Exception as e:
                self._log.error(f"Failed to fetch OKX article page: {e} {traceback.format_exc()}")
                pass

        return AnnouncementType.OTHER

    def extract_source_id(self, item: Dict) -> str:
        return item.get('id', '')

    def extract_title(self, item: Dict) -> str:
        return item.get('title', '')

    def extract_body(self, item: Dict) -> str:
        return ""

    def extract_timestamp(self, item: Dict) -> int:
        created_at = item.get('publishTime')
        if not created_at:
            return 0

        return created_at

    def build_url(self, item: Dict) -> str:
        slug = item.get('slug', '')
        return f"https://www.okx.com/help/{slug}" if slug else ""
