from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


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
    original_category: str  # Keep original category for reference
    categories: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash((self.exchange, self.source_id))
