import re
from typing import List, Set


class TickerParser:
    """Advanced ticker extraction with multi-ticker support and universal fallback"""

    # Class-level constants
    SECOND_PAIR_TOKENS = ['USDT', 'USDC', 'FUSDT', 'BTC', 'ETH', 'BNB', 'USD1']  # Added USD1

    BLACKLIST = {
        # Second pair tokens
        'USDT', 'USDC', 'FUSDT', 'BTC', 'ETH', 'BNB', 'USD1',  # Added USD1
        # Common terms and exchanges
        'USD', 'APR', 'UTC', 'AI', 'WEB', 'KRW',
        'MEXC', 'BINGX', 'BITHUMB', 'UPBIT', 'GATE', 'BITGET', 'HTX',
        'BINANCE', 'KUCOIN', 'OKX', 'BYBIT', 'KRAKEN', 'BITSTAMP', 'BITFINEX',
        'COINBASE', 'LBANK', 'POLONIEX', 'BITMEX', 'HUOBI', 'COINLIST',
        # Single letters that often appear in regular text (removed common single letters)
        # Keep only clearly non-ticker single letters

    }

    # Default patterns for universal extraction
    DEFAULT_PATTERNS = [
        # Tickers in parentheses: "Name (TICKER)"
        r'\(\s*([A-Z0-9][A-Z0-9]{0,11})\s*\)',
        # Trading pairs: "LEVERUSDT", "HEMIUSDTM"
        r'\b([A-Z0-9][A-Z0-9]{1,14})(?:USDT|USDC|BTC|ETH|BNB|USD1)(?:M)?\b',
        # Before trading pair suffix (extracts base ticker)
        r'\b([A-Z0-9][A-Z0-9]{0,11})(?=(?:USDT|USDC|BTC|ETH|BNB|USD1))',
        # Tickers in lists: "LEVER, HEMI & TOKEN"
        r'(?:^|[\s,&/])([A-Z0-9][A-Z0-9]{0,11})(?=[\s,&/)]|$)',
        # Standalone all-caps words (including single letters and numbers)
        r'(?:^|\s)([A-Z0-9][A-Z0-9]{0,11})(?=\s|$)',
    ]

    @classmethod
    def extract_tickers(cls, title: str, body: str = "", patterns: List[str] = None) -> List[str]:
        """
        Extract tickers from text using provided patterns or default universal patterns.

        Args:
            title: Title text to search
            body: Additional body text to search
            patterns: Optional list of regex patterns. If None, uses DEFAULT_PATTERNS

        Returns:
            Sorted list of unique tickers found
        """
        text = f"{title} {body or ''}"

        text = re.sub(r'([A-Z0-9]+), ([A-Z0-9]+) and ([A-Z0-9]+)', r'\1, \2, \3,', text) # Replace "PLTR, NFLX and MSTR " with "PLTR, NFLX, MSTR, "
        # print(patterns, text)
        # print(text)
        # Use provided patterns or default ones
        patterns_to_use = patterns if patterns else cls.DEFAULT_PATTERNS
        # patterns_to_use = ['(\\b[A-Z0-9]+\\b)']
        # print("patterns_to_use", patterns_to_use)
        all_tickers = set()

        for pattern in patterns_to_use:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    # Handle multiple capture groups
                    for group in match:
                        if group:
                            # Extract alphanumeric uppercase sequences
                            tickers = cls._extract_valid_tickers(group)
                            all_tickers.update(tickers)
                elif isinstance(match, str):
                    tickers = cls._extract_valid_tickers(match)
                    all_tickers.update(tickers)

        # Apply filtering and cleanup
        filtered_tickers = cls._filter_tickers(all_tickers)

        return sorted(list(filtered_tickers))

    @classmethod
    def _extract_valid_tickers(cls, text: str) -> Set[str]:
        """
        Extract valid ticker symbols from text.
        Only matches sequences that are ALL uppercase (not just starting with uppercase).
        Now allows single character tickers and numeric sequences.
        """
        # Match sequences that are entirely uppercase letters and numbers
        # Can start with letter or number, minimum 1 character
        pattern = r'\b([A-Z0-9]+)\b'
        matches = re.findall(pattern, text)

        valid_tickers = set()
        for match in matches:
            # Check if the match is actually all uppercase in the original text
            # This prevents matching "Mar" as "M"
            if match == match.upper() and len(match) <= 12:
                valid_tickers.add(match)
        # print("valid_tickers", valid_tickers)
        return valid_tickers

    @classmethod
    def _filter_tickers(cls, tickers: Set[str]) -> Set[str]:
        """
        Filter out invalid tickers, blacklisted terms, and clean up trading pair suffixes.
        """
        # Remove pure digits (but allow alphanumeric like "10000WHY")
        filtered = {t for t in tickers if not t.isdigit()}

        # Remove blacklisted terms
        filtered = {t for t in filtered if t not in cls.BLACKLIST}

        # Remove trading pair suffixes
        suffix_pattern = f'({"|".join(cls.SECOND_PAIR_TOKENS)})$'
        cleaned = set()
        for ticker in filtered:
            # Remove suffix if present
            cleaned_ticker = re.sub(suffix_pattern, '', ticker)
            if cleaned_ticker and cleaned_ticker not in cls.BLACKLIST:
                cleaned.add(cleaned_ticker)

        return cleaned
