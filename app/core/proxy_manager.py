import asyncio
from typing import List, Optional, Dict


class ExchangeProxyManager:
    """Manages proxy rotation per exchange"""

    def __init__(self):
        self._rotators: Dict[str, ProxyRotator] = {}
        self._lock = asyncio.Lock()

    def register_exchange(self, exchange: str, proxies: List[str]):
        """Register proxy list for an exchange"""
        if proxies:
            self._rotators[exchange] = ProxyRotator(proxies)

    async def get_proxy(self, exchange: str) -> Optional[str]:
        """Get next proxy for exchange"""
        rotator = self._rotators.get(exchange)
        return await rotator.next_proxy() if rotator else None


class ProxyRotator:
    """Round-robin proxy rotation for a single exchange"""

    def __init__(self, proxies: List[str]):
        self._proxies = proxies or []
        self._index = 0
        self._lock = asyncio.Lock()

    async def next_proxy(self) -> Optional[str]:
        if not self._proxies:
            return None

        async with self._lock:
            proxy = self._proxies[self._index]
            self._index = (self._index + 1) % len(self._proxies)
            return proxy
