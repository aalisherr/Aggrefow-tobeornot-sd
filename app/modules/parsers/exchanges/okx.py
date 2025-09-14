import json
import traceback

from bs4 import BeautifulSoup
from typing import Dict, Any, List
from app.modules.parsers.exchanges.base import ExchangeScraper
from app.core.models import AnnouncementType


class OkxScraper(ExchangeScraper):
    """OKX scraper with category-based classification"""

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
            #
            # for item in items:
            #     item['publishTime'] = self.convert_date_to_timestamp(item['publishTime'])

            return items

        except (json.JSONDecodeError, AttributeError) as e:
            self._log.error(f"Failed to parse OKX HTML data: {e}")
            return []

    async def extract_category(self, item: Dict) -> str:
        title = item.get('title', '').lower()

        if category := self.get_category_by_title(title):
            return category.original_ids[0]

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

        return self.convert_date_to_timestamp(created_at)

    def build_url(self, item: Dict) -> str:
        slug = item.get('slug', '')
        return f"https://www.okx.com/help/{slug}" if slug else ""
