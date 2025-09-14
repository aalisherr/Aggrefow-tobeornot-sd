import asyncio
import json
import random
from typing import Union
from urllib.parse import urlparse


async def random_delay(base_delay: Union[int, float], randomness_percent: float = 10.0) -> None:
    """
    Wait for a random duration around the base delay with specified randomness.

    Args:
        base_delay: The base delay in seconds
        randomness_percent: Percentage of randomness (default: 10%)

    Example:
        await random_delay(1.0)  # Wait between 0.9 and 1.1 seconds
        await random_delay(2.0, 20.0)  # Wait between 1.6 and 2.4 seconds
    """
    if base_delay <= 0:
        return

    # Calculate random factor (e.g., 0.9 to 1.1 for 10% randomness)
    random_factor = 1 + random.uniform(-randomness_percent / 100, randomness_percent / 100)

    # Calculate final delay time
    actual_delay = base_delay * random_factor

    # Ensure delay is not negative
    actual_delay = max(actual_delay, 0.001)  # Minimum 1ms to avoid negative/zero delays

    await asyncio.sleep(actual_delay)

def truncate_content(content: str, max_length: int = 500) -> str:
    """Truncate long content for better error readability"""
    if len(content) <= max_length:
        return content
    return content[:max_length] + f"... [truncated, total {len(content)} characters]"

def get_json_if_valid(json_str: str) -> str:
    try:
        return json.loads(json_str)
    except Exception:
        return json_str
