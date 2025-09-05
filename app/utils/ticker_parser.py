"""app/utils/ticker_parser.py"""
import re
from typing import List, Set


class TickerParser:
    """Advanced ticker extraction with multi-ticker support"""

    # Separators used in announcements
    SEPARATORS = [
        ',', '、', ' and ', ' And ', ' AND ', '/', '／', '&', ' & ',
        ', ', '，', ' + ', '+', ' | ', '|'
    ]

    # Common false positives to filter out
    BLACKLIST = {
        'AND', 'OR', 'THE', 'ON', 'WILL', 'LAUNCH', 'USDT', 'USD',
        'MARGIN', 'MARGINED', 'SPOT', 'FUTURES', 'PERPETUAL', 'CONTRACT',
        'TRADING', 'BOTS', 'USDⓈ', 'COIN', 'TOKEN', 'NEW', 'LISTING',
        'LIST', 'LISTS', 'ALPHA', 'BETA', 'PERP', 'MARGINED'
    }

    @classmethod
    def extract_tickers(cls, title: str, body: str = "") -> List[str]:
        """Extract all tickers from announcement text"""
        text = f"{title} {body or ''}"
        tickers = set()

        # Pattern 1: Tickers in parentheses (BTC), (ETH), (Q)
        pattern1 = r'\(([A-Z0-9]{1,15})\)'
        for match in re.finditer(pattern1, text):
            ticker = match.group(1).upper()
            if ticker not in cls.BLACKLIST and len(ticker) >= 1:
                tickers.add(ticker)

        # Pattern 2: XXXUSDT patterns - extract only the base ticker
        pattern2 = r'\b([A-Z0-9]{2,15})USDT[M]?\b'
        for match in re.finditer(pattern2, text, re.IGNORECASE):
            ticker = match.group(1).upper()
            if ticker not in cls.BLACKLIST and len(ticker) >= 2:
                tickers.add(ticker)

        # Pattern 3: Slash pairs XXX/USDT, XXX／USDT - extract only base ticker
        pattern3 = r'\b([A-Z0-9]{2,15})[/／](?:USDT|USD)\b'
        for match in re.finditer(pattern3, text, re.IGNORECASE):
            ticker = match.group(1).upper()
            if ticker not in cls.BLACKLIST and len(ticker) >= 2:
                tickers.add(ticker)

        # Pattern 4: "will list XXX" or "listing XXX"
        pattern4 = r'\b(?:will list|listing|lists?|launch|add(?:ing)?|support(?:ing)?)\s+([A-Z0-9]{2,15})\b'
        for match in re.finditer(pattern4, text, re.IGNORECASE):
            ticker = match.group(1).upper()
            if ticker not in cls.BLACKLIST and len(ticker) >= 2:
                tickers.add(ticker)

        # Pattern 5: Multiple tickers with ampersand or "and"
        pattern5 = r'\b([A-Z0-9]{2,8})\s*(?:&|and|And|AND)\s*([A-Z0-9]{2,8})\b'
        for match in re.finditer(pattern5, text):
            t1, t2 = match.group(1).upper(), match.group(2).upper()
            if t1 not in cls.BLACKLIST:
                tickers.add(t1)
            if t2 not in cls.BLACKLIST:
                tickers.add(t2)

        # Pattern 6: Tickers mentioned after specific verbs
        pattern6 = r'\b(?:list(?:ed|ing)?|launch(?:ed|ing)?|add(?:ed|ing)?|support(?:ed|ing)?)\s+([A-Z0-9]{2,15})(?:\s+|$|,)'
        for match in re.finditer(pattern6, text, re.IGNORECASE):
            ticker = match.group(1).upper()
            if ticker not in cls.BLACKLIST and len(ticker) >= 2:
                tickers.add(ticker)

        # Clean up: Remove any tickers that contain "USDT" or other blacklisted substrings
        filtered_tickers = set()
        for ticker in tickers:
            # Skip if ticker contains any blacklisted substring
            if any(blacklisted in ticker for blacklisted in cls.BLACKLIST):
                continue
            # Skip if ticker ends with USDT-related patterns
            if ticker.endswith(('USDT', 'USD', 'PERP', 'MARGIN')):
                continue
            filtered_tickers.add(ticker)

        # Sort and limit
        result = sorted(list(filtered_tickers))
        return result[:10]  # Limit to 10 tickers max

