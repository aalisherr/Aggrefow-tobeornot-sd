import json
from typing import Dict, Any, List

from bs4 import BeautifulSoup

from app.modules.parsers.exchanges.base import ExchangeScraper
from app.modules.parsers.generators.binance_cookies.aws_waf_solver import AsyncAwsWafSolver


class BinanceScraper(ExchangeScraper):
    """Binance scraper with category-based classification"""

    async def initialize(self):
        self.initialize_headers()
        await self.change_proxy()

        await self.set_api_url()
        self._log.debug(f"Initialized with URL: {self.api_url}")

        solver = AsyncAwsWafSolver(self.http.session)
        await solver.solve(self.api_url)

    def extract_items(self, raw_data: Any) -> List[Dict]:
        try:
            soup = BeautifulSoup(raw_data, 'html.parser')
            script_tag = soup.find('script', {'id': '__APP_DATA'})

            if not script_tag:
                self._log.error("Could not find __APP_DATA script tag")
                return []

            json_data = json.loads(script_tag.string)
            items = (json_data.get('appState', {})
                     .get('loader', {})
                     .get('dataByRouteId', {})
                     .get('d72f', {})
                     .get('articles', []))

            return items

        except (json.JSONDecodeError, AttributeError) as e:
            self._log.error(f"{self.name} | Failed to parse B HTML data: {e}")
            return []

    async def extract_category(self, item: Dict) -> str:
        return item.get("catalogName", "")

    def extract_source_id(self, item: Dict) -> str:
        return item.get("code", "")

    def extract_title(self, item: Dict) -> str:
        return self.strip_html(item.get("title", ""))

    def extract_body(self, item: Dict) -> str:
        return self.strip_html(item.get("body", ""))

    def extract_timestamp(self, item: Dict) -> int:
        return int(item.get("publishDate", 0))

    def build_url(self, item: Dict) -> str:
        if code := self.extract_source_id(item):
            return f"{self._base_url}/en/support/announcement/detail/{code}"
        return f"{self._base_url}/en/support/announcement"
