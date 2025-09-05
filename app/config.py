import os
import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: int
    proxies: List[str]
    db_path: str
    poll_interval: float
    user_agent: str
    demo_mode: bool

    # Redis
    redis_url: str = "redis://localhost:6379"
    use_fakeredis: bool = True  # For testing

    # Thread mapping (new format)
    thread_mapping_config: Dict = None

    @classmethod
    def from_env(cls) -> 'Config':
        load_dotenv()

        thread_config = os.getenv("TELEGRAM_THREAD_CONFIG", "{}")
        thread_mapping = json.loads(thread_config)

        proxies = [p.strip() for p in os.getenv("PROXIES", "").split(",") if p.strip()]

        return cls(
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            use_fakeredis=os.getenv("USE_FAKEREDIS", "true").lower() in ("1", "true", "yes"),
            thread_mapping_config=thread_mapping,
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=int(os.getenv("TELEGRAM_CHAT_ID", "0")),
            proxies=proxies,
            db_path=os.getenv("DB_PATH", "announcements.db"),
            poll_interval=float(os.getenv("POLL_INTERVAL", "60")),
            user_agent=os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; CryptoBot/1.0)"),
            demo_mode=os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes"),
        )