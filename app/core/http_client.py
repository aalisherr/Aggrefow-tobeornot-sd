import json
import asyncio
from typing import Optional, Any, Dict
from urllib.parse import urlparse

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from curl_cffi.requests import AsyncSession

from app.core.models.exceptions import InvalidResponseException
from app.core.proxy_manager import ExchangeProxyManager
from app.utils.tools import truncate_content


class HttpClient:
    """HTTP client with per-exchange proxy support using curl_cffi"""

    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        "Connection": "keep-alive",
    }

    def __init__(self, proxy_manager: ExchangeProxyManager, exchange_name: Optional[str] = None, timeout: int = 20):
        self._proxy_manager = proxy_manager
        self.exchange_name = exchange_name
        self._timeout = timeout
        self.session: Optional[AsyncSession] = (
            AsyncSession(
                headers=self.DEFAULT_HEADERS.copy(),
                timeout=self._timeout,
                impersonate="chrome"
            )
        )

        self._log = logger.bind(component="http", exchange=exchange_name)

    # async def get_proxy_for_exchange(self, exchange: str) -> Optional[str]:
    #     """Get proxy for specific exchange"""
    #     return await self._proxy_manager.get_proxy(exchange)

    async def request(self, method: str, url: str, **kwargs):
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            reraise=True,
            before_sleep=lambda retry_state, **kwargs:
                logger.info(f"{self.exchange_name} №{retry_state.attempt_number} | "
                            f"{truncate_content(str(retry_state.outcome.exception()).replace('{', '[').replace('}', ']'))}")
        )
        async def request_inner() -> str:
            proxy = kwargs.pop('proxy', None)
            if proxy:
                kwargs['proxies'] = {'http': proxy, 'https': proxy}
            # print(url, method, kwargs, self.session.headers)
            response = await self.session.request(method, url, **kwargs)

            if not response.ok:
                raise InvalidResponseException(response.text)

            return response.text

        return await request_inner()

    async def request_json(self, method: str, url: str, **kwargs) -> Any:
        resp = await self.request(method, url, **kwargs)
        return json.loads(resp)

    async def get(self, url: str, **kwargs):
        return await self.request_json("GET", url, **kwargs)

    async def post(self, url: str, **kwargs):
        return await self.request_json("POST", url, **kwargs)

    async def close(self):
        if self.session:
            await self.session.close()

    @staticmethod
    def get_base_url(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"