import re
import traceback
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from loguru import logger

from app.models.announcement import Announcement, AnnouncementType
from app.config.loader import ExchangeConfig
from app.core.http_client import HttpClient
from app.db.repository import AnnouncementRepository


class ExchangeScraper(ABC):
    """Base class with category-based classification"""

    def __init__(
            self,
            config: ExchangeConfig,
            http_client: HttpClient,
            repository: AnnouncementRepository
    ):
        self.config = config
        self.exchange_name = config.name
        self.http = http_client
        self.repo = repository
        self._log = logger.bind(exchange=self.exchange_name)
        self.original_category_mappings = self._get_original_category_mappings()

        self.url = None
        self.headers = None

    async def initialize(self):
        self.initialize_headers()
        await self.change_proxy()

        print(self.http.session.headers)
        self.url = await self.get_api_url()
        print(self.url)

    def initialize_headers(self):
        """Get headers"""
        headers = self.http.DEFAULT_HEADERS
        self.http.session.headers.update(headers)

    async def change_proxy(self):
        proxy = await self.http.get_proxy_for_exchange(self.exchange_name)
        self.http.session.proxies.update({"http": proxy, "https": proxy})

    async def get_actual_api_url(self, raw_api_url: str, navigation_id_placeholder: str) -> str:
        url = raw_api_url.split('_next/')[0]
        resp_text = await self.http.request("GET", url, headers=self.headers)

        # Look for the build ID pattern in Bithumb's Next.js structure
        pattern = r'/_next/static/([^/]+)/_buildManifest\.js'
        match = re.search(pattern, resp_text)

        if match:
            build_id = match.group(1)
            actual_api_url = raw_api_url.replace(navigation_id_placeholder, build_id)
            return actual_api_url
        else:
            print(f"Build ID not found in the HTML / Failed to fetch page: {resp_text[:-500]}")
            raise Exception("Build ID not found in the HTML")

    async def get_api_url(self) -> str:
        navigation_id_placeholder = "[navigation_id]"
        raw_api_url = self.config.api_url

        if navigation_id_placeholder in raw_api_url:
            return await self.get_actual_api_url(raw_api_url, navigation_id_placeholder)

        return raw_api_url

    def _get_original_category_mappings(self):
        return {k.lower(): v for k, v in self.config.category_mappings.items()}

    async def fetch_raw_announcements(self) -> Any:
        await self.change_proxy()
        return await self.fetch_raw_data()

    @abstractmethod
    async def fetch_raw_data(self) -> Any:
        """Fetch raw data from exchange API"""
        pass

    @abstractmethod
    def extract_items(self, raw_data: Any) -> List[Dict]:
        """Extract announcement items from raw response"""
        pass

    @abstractmethod
    async def extract_category(self, item: Dict) -> str:
        """Extract category from raw item"""
        pass

    @abstractmethod
    def build_url(self, item: Dict) -> str:
        """Build announcement URL"""
        pass

    def classify_by_category(self, category: str) -> AnnouncementType:
        """Classify using configured category mappings"""
        if not category:
            return AnnouncementType.OTHER

        # Direct mapping lookup
        mapped_type = self.original_category_mappings.get(category.lower())
        if mapped_type:
            try:
                return AnnouncementType(mapped_type)
            except ValueError:
                self._log.warning(f"Invalid type mapping: {category} -> {mapped_type}")

        # Log unmapped categories for future configuration
        self._log.debug(f"{self.exchange_name} Unmapped category: {category}")
        return AnnouncementType.OTHER

    async def parse_announcement(self, item: Dict[str, Any]) -> Optional[Announcement]:
        """Parse announcement with category-based classification"""
        source_id = self.extract_source_id(item)
        if not source_id:
            return None

        title = self.extract_title(item)
        body = self.extract_body(item)
        published_ms = self.extract_timestamp(item)
        category = await self.extract_category(item)
        url = self.build_url(item)

        # Use category mapping for classification
        ann_type = self.classify_by_category(category)

        # Extract tickers
        tickers = self.extract_tickers(title, body)

        return Announcement(
            exchange=self.exchange_name,
            source_id=source_id,
            tickers=tickers,
            title=title,
            url=url,
            published_at_ms=published_ms,
            body_text=body[:500] if body else None,
            classified_type=ann_type,
            original_category=category,
            categories=[category] if category else []
        )

    async def fetch_latest(self) -> (List[Announcement], int):
        """Main fetch method"""
        try:
            raw_data = await self.fetch_raw_announcements()

            items = self.extract_items(raw_data)
            sorted_items = self.sort_items_by_date(items)

            announcements = []
            latest_known_ms = await self.repo.get_latest_published_ms(self.exchange_name) or 0

            for item in sorted_items:
                try:
                    ann = await self.parse_announcement(item)

                    if not ann:
                        continue

                    if ann.published_at_ms > latest_known_ms:
                        announcements.append(ann)
                    else:
                        break  # Assuming sorted by date

                except Exception as e:
                    self._log.warning(f"Parse error: {e}")

            return announcements, len(items)

        except Exception as e:
            self._log.error(f"Fetch failed: {e.__str__()} {traceback.format_exc()}")
            return [], 0

    def sort_items_by_date(self, items: List[Dict]) -> List[Dict]:
        return sorted(items, key=lambda x: self.extract_timestamp(x), reverse=True)

    # Abstract methods for data extraction
    @abstractmethod
    def extract_source_id(self, item: Dict) -> str:
        pass

    @abstractmethod
    def extract_title(self, item: Dict) -> str:
        pass

    @abstractmethod
    def extract_body(self, item: Dict) -> str:
        pass

    @abstractmethod
    def extract_timestamp(self, item: Dict) -> int:
        pass

    def extract_tickers(self, title: str, body: str = "") -> List[str]:
        """Extract tickers - can be overridden per exchange"""
        from app.utils.ticker_parser import TickerParser
        return TickerParser.extract_tickers(title, body)

    @staticmethod
    def change_items_key(items: List[Dict], old_key: str, new_key: str):
        for item in items:
            item[new_key] = item.pop(old_key)

        return items

    @staticmethod
    def strip_html(text: str) -> str:
        """Remove HTML tags"""
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&[a-z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def convert_date_to_timestamp(date_str: str) -> int:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return int(dt.timestamp()) * 1000
        except:
            return 0
