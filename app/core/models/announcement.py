from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from app.db.config.loader import CategoryMapping


class AnnouncementType(str, Enum):
    """Unified announcement types across all exchanges"""
    LISTING_SPOT = "listing_spot"
    LISTING_FUTURES = "listing_futures"
    DELISTING = "delisting"
    ACTIVITY = "activities"
    MAINTENANCE = "maintenance"
    NEWS = "news"
    OTHER = "other"


@dataclass
class Announcement:
    exchange: str
    source_id: str
    tickers: List[str]
    title: str
    url: str
    published_at_ms: int
    body_text: Optional[str]
    classified_type: AnnouncementType
    category: CategoryMapping

    def __hash__(self):
        return hash((self.exchange, self.source_id))
