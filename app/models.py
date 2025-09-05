"""app/models.py"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class AnnouncementType(str, Enum):
    LISTING_SPOT = "listing_spot"
    LISTING_FUTURES = "listing_futures"
    DELISTING = "delisting"
    ACTIVITY = "activity"
    NEWS = "news"
    MAINTENANCE = "maintenance"
    OTHER = "other"


@dataclass
class Announcement:
    exchange: str
    source_id: str
    tickers: List[str]  # Changed from ticker: Optional[str]
    title: str
    url: str
    published_at_ms: int
    body_text: Optional[str]
    classified_type: AnnouncementType
    categories: List[str] = field(default_factory=list)  # Added for thread mapping

    def __hash__(self):
        return hash((self.exchange, self.source_id))

    @property
    def ticker(self) -> Optional[str]:
        """Backward compatibility - returns first ticker"""
        return self.tickers[0] if self.tickers else None