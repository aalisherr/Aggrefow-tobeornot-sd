import json
import asyncio
from typing import Optional, Any, Dict

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from curl_cffi.requests import AsyncSession
from app.core.proxy_manager import ExchangeProxyManager
from app.utils.tools import truncate_content


class HttpClient:
    """HTTP client with per-exchange proxy support using curl_cffi"""

    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        "Connection": "keep-alive",
    }

    def __init__(self, proxy_manager: ExchangeProxyManager, timeout: int = 20):
        self._proxy_manager = proxy_manager
        self._timeout = timeout
        self.session: Optional[AsyncSession] = (
            AsyncSession(
                headers=self.DEFAULT_HEADERS.copy(),
                timeout=self._timeout,
                impersonate="chrome120"
            )
        )

        self._log = logger.bind(component="http")

    async def get_proxy_for_exchange(self, exchange: str) -> Optional[str]:
        """Get proxy for specific exchange"""
        return await self._proxy_manager.get_proxy(exchange)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def request(self, method: str, url: str, **kwargs) -> str:
        if proxy := kwargs.pop('proxy', None):
            kwargs['proxies'] = {'http': proxy, 'https': proxy}

        try:
            response = await self.session.request(method, url, **kwargs)
            resp_msg = response.text

            if response.status_code >= 400:
                truncated = truncate_content(resp_msg)

                # Log detailed error information
                logger.error(
                    f"HTTP Error {response.status_code} for {url}\n"
                    f"Headers: {dict(response.headers)}\n"
                    f"Error preview: {truncated}"
                )

                response.raise_for_status()

            return resp_msg

        except aiohttp.ClientError as e:
            logger.error(f"Request failed for {url}: {type(e).__name__}: {str(e)}")
            raise

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
