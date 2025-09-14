import string

from app.core.models import Announcement, AnnouncementType


class MessageFormatter:
    """Format announcements for different notification channels"""

    @staticmethod
    def format_telegram(ann: Announcement) -> str:
        """Format announcement for Telegram"""
        exchange = ann.exchange.capitalize()
        action = string.capwords(ann.category.show_name.replace("_", " "))
        
        msg = f"<b>{exchange}</b> [{action}]"

        if ann.classified_type in [
            AnnouncementType.LISTING_SPOT,
            AnnouncementType.LISTING_FUTURES,
            AnnouncementType.DELISTING
        ]:
            # Use tickers list instead of single ticker
            if ann.tickers:
                ticker_str = ", ".join([f"${t}" for t in ann.tickers[:3]])
                if len(ann.tickers) > 3:
                    ticker_str += f" +{len(ann.tickers) - 3} more"
            else:
                ticker_str = ""

            msg += f" {ticker_str}"

        msg += f": {ann.title}"

        hyper_link_msg = f"<a href='{ann.url}'>{msg}</a>"
        return hyper_link_msg
