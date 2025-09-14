import re
import time
import traceback
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from loguru import logger

from app.core.models import Announcement, AnnouncementType
from app.db.config.loader import ExchangeConfig, CategoryMapping
from app.core.http_client import HttpClient
from app.db.repository import AnnouncementRepository
from app.utils.ticker_parser import TickerParser
from app.utils.tools import get_json_if_valid


class ExchangeScraper(ABC):
    """Base class with category-based classification"""

    def __init__(
            self,
            config: ExchangeConfig,
            http_client: HttpClient,
            repository: AnnouncementRepository
    ):
        self.api_url = config.api_url
        self.method = config.request.method
        self.kwargs = config.request.kwargs
        self.headers = config.headers
        self.proxies = config.proxies
        self.categories = config.categories
        self.name = config.name
        self.poll_interval = config.monitoring.poll_interval
        self.patterns = config.patterns

        self.http = http_client
        self.repo = repository
        self._log = logger.bind(exchange=self.name)
        # self._log.info("Initialized with URL")

        self._base_url = self.http.get_base_url(self.api_url)

    async def initialize(self):
        self.initialize_headers()
        await self.change_proxy()

        await self.set_api_url()
        self._log.debug(f"Initialized with URL: {self.api_url}")

    def initialize_headers(self):
        """Get headers from config"""
        self.http.session.headers.update(self.headers)

    async def change_proxy(self):
        """Change proxy from the pool"""
        if self.proxies:
            # For now, use first proxy or implement rotation
            proxy = self.proxies[0]
            self.http.session.proxies.update({"http": proxy, "https": proxy})

    async def get_actual_api_url(self, raw_api_url: str, placeholder: str = "{navigation_id}") -> str:
        """Resolve dynamic parts in API URL"""
        if placeholder not in raw_api_url:
            return raw_api_url

        # Extract base URL for fetching navigation ID
        url_parts = raw_api_url.split('/_next/')
        if len(url_parts) < 2:
            return raw_api_url

        base_url = url_parts[0]

        try:
            resp_text = await self.http.request("GET", base_url, headers=self.headers)

            # Look for build ID pattern
            pattern = r'/_next/static/([^/]+)/_buildManifest\.js'
            match = re.search(pattern, resp_text)

            if match:
                build_id = match.group(1)
                actual_api_url = raw_api_url.replace(placeholder, build_id)
                return actual_api_url
            else:
                self._log.warning(f"Build ID not found, using URL as-is")
                return raw_api_url

        except Exception as e:
            self._log.error(f"Failed to resolve dynamic URL: {e}")
            return raw_api_url

    async def set_api_url(self) -> None:
        """Get the final API URL"""
        raw_api_url = self.api_url

        # Check for navigation_id placeholder
        if "{navigation_id}" in raw_api_url:
            self.api_url = await self.get_actual_api_url(raw_api_url)

    async def fetch_raw_data(self) -> str:
        kwargs = self.kwargs.copy()

        return await self.http.request(self.method,
            self.api_url,
            **kwargs,
        )

    async def fetch_raw_announcements(self) -> Any:
        """Fetch raw data with proxy rotation if needed"""
        # Could implement proxy rotation here
        if self.proxies and len(self.proxies) > 1:
            # Simple rotation: use next proxy
            await self.change_proxy()

        raw_data = await self.fetch_raw_data()
        return get_json_if_valid(raw_data)

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

    def get_category_by_title(self, title: str) -> Optional[CategoryMapping]:
        for category in self.categories:
            if title_regex := category.title_regex:
                if re.search(title_regex, title):
                    return category
        return None

    def classify_by_category(self, category: str, default_category: CategoryMapping =
        CategoryMapping(internal_name="other", show_name="Other", original_ids=[])) -> CategoryMapping:
        """Classify using configured category mappings"""
        if not category:
            return default_category

        # Check if category matches any original_ids in the new structure
        for category_config in self.categories:
            if str(category).lower() in [str(_id).lower() for _id in category_config.original_ids]:
                try:
                    return category_config
                except ValueError:
                    self._log.warning(f"Invalid type mapping: {category} -> {category_config.internal_name}")
                    return default_category

        # Log unmapped categories for future configuration
        self._log.debug(f"{self.name} Unmapped category: {category}")
        return default_category

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
        category = self.classify_by_category(category)

        # Extract tickers
        tickers = self.extract_tickers(title)
        # print(tickers, title)
        return Announcement(
            exchange=self.name,
            source_id=source_id,
            tickers=tickers,
            title=title,
            url=url,
            published_at_ms=published_ms,
            body_text=body[:500] if body else None,
            classified_type=AnnouncementType(category.internal_name),
            category=category
        )

    async def fetch_latest(self) -> (List[Announcement], int):
        """Main fetch method"""
        try:
            raw_data = await self.fetch_raw_announcements()
            items = self.extract_items(raw_data)
            sorted_items = self.sort_items_by_date(items)

            announcements = await self._process_items(sorted_items)

            return announcements, len(items)

        except Exception as e:
            self._log.error(f"{self.name} | Fetch failed: {e} {traceback.format_exc()}")
            return [], 0

    async def _process_items(self, sorted_items: list) -> List[Announcement]:
        """Process sorted items and filter new announcements"""
        announcements = []
        # current_time_ms = int(time.time() * 1000)
        current_latest_ms = await self.repo.get_latest_published_ms(self.name) or 0

        for i, item in enumerate(sorted_items):
            try:
                if not (ann := await self.parse_announcement(item)):
                    continue

                # print(self.name, ann.source_id, await self.repo.is_announcement_exists(self.name, ann.source_id))
                # # Skip future listings that already exist
                # if (await self.repo.is_announcement_exists(self.name, ann.source_id)
                #         and current_time_ms < ann.published_at_ms):
                #     current_latest_ms = await self.repo.get_latest_published_ms(self.name, i + 1) or 0
                #     continue
                # print(ann.published_at_ms, current_latest_ms, ann.tickers)
                # Stop processing if we've reached older announcements
                if ann.published_at_ms < current_latest_ms or await self.repo.is_announcement_exists(self.name, ann.source_id):
                    break
                # print(item)

                announcements.append(ann)

            except Exception as e:
                self._log.warning(f"Parse error: {e} {traceback.format_exc()}")

        return announcements

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
        return TickerParser.extract_tickers(title=title, body=body, patterns=self.patterns)

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
            