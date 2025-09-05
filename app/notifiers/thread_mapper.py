"""app/notifiers/thread_mapper.py"""
import json
from typing import Dict, Optional, List
from app.models.announcement import Announcement, AnnouncementType


class ThreadMapper:
    """Maps announcements to Telegram threads based on flexible rules"""

    def __init__(self, thread_mappings: List[Dict], default_thread: int):
        """
        Config format:
        {
            "mappings": [
                {
                    "thread_id": 12345,
                    "name": "Major Spot Listings",
                    "rules": {
                        "exchanges": ["binance", "kucoin", "bybit"],
                        "types": ["listing_spot"]
                    }
                },
                {
                    "thread_id": 23456,
                    "name": "Tier 2/3 Exchanges",
                    "rules": {
                        "exchanges": ["mexc", "gate"],
                        "types": ["listing_spot", "listing_futures"]
                    }
                },
                {
                    "thread_id": 34567,
                    "name": "Activities",
                    "rules": {
                        "exchanges": ["binance", "bybit"],
                        "types": ["activity"]
                    }
                }
            ],
            "default_thread": 99999,
            "legacy_map": {"binance": 11111}  # Backward compatibility
        }
        """
        self.mappings = thread_mappings
        self.default_thread = default_thread

    def get_thread_id(self, ann: Announcement) -> Optional[int]:
        """Get thread ID for announcement based on rules"""
        # Check rule-based mappings
        for mapping in self.mappings:
            rules = mapping.get("rules", {})

            # Check exchange match
            exchanges = rules.get("exchanges", [])
            if exchanges and ann.exchange.lower() not in [e.lower() for e in exchanges]:
                continue

            # Check type match
            types = rules.get("types", [])
            if types and ann.classified_type.value not in types:
                continue

            # Check category match (if specified)
            categories = rules.get("categories", [])
            if categories:
                ann_cats = [c.lower() for c in ann.categories]
                if not any(cat.lower() in ann_cats for cat in categories):
                    continue

            # All rules matched
            return mapping.get("thread_id")

        # Use default thread
        return self.default_thread

    @classmethod
    def from_env(cls, json_str: str) -> 'ThreadMapper':
        """Create from JSON environment variable"""
        try:
            if json_str.startswith("{") and "mappings" not in json_str:
                # Legacy format: {"binance": 123, "bybit": 456}
                return cls({"legacy_map": json.loads(json_str)})
            else:
                # New format with mappings
                return cls(json.loads(json_str))
        except:
            return cls({})