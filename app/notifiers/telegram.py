import aiohttp
from loguru import logger
from typing import Optional


class TelegramNotifier:
    """Telegram notification handler with a persistent session."""

    def __init__(self, bot_token: str, chat_id: int):
        self._token = bot_token
        self._chat_id = chat_id
        self._log = logger.bind(component="telegram")
        self._session: Optional[aiohttp.ClientSession] = None

        self.init()

    def init(self):
        """Initializes the aiohttp session."""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))

    async def close(self):
        """Closes the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def send_with_thread(self, exchange: str, text: str, thread_id: int) -> bool:
        """Send message to Telegram with specific thread ID using a persistent session."""
        if not self._token or not thread_id:
            self._log.warning("Missing token or thread_id", exchange=exchange)
            return False

        if not self._session:
            self._log.error("Notifier session not initialized. Call init() first.")
            return False

        payload = {
            "chat_id": self._chat_id,
            "message_thread_id": thread_id,
            "text": text,
            "disable_web_page_preview": True,
            "parse_mode": "HTML",
        }

        url = f"https://api.telegram.org/bot{self._token}/sendMessage"

        data = ""
        try:
            async with self._session.post(url, json=payload) as resp:
                data = await resp.json(content_type=None)
                # print(data)
                success = resp.status == 200 and data.get("ok")
                if success:
                    self._log.debug("Message sent successfully", exchange=exchange)
                else:
                    self._log.warning(
                        f"Failed to send message | {data}",
                        exchange=exchange,
                        status=resp.status
                    )
                return success
        except Exception as e:
            self._log.error(f"Send error: {e} | {data}", exchange=exchange)
            return False