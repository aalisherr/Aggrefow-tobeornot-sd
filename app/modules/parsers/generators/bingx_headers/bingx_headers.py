"""
Python implementation for generating API headers with signature
"""
import hashlib
import json
import time
import uuid
from typing import Dict, Any, Optional


class BingxHeaderGenerator:
    """Generate headers with signature for API requests"""

    # Secret keys from the JavaScript code
    ENCRYPTION_KEYS = {
        'p1': '95d65c73dc5c437',
        'p2': '0ae9018fb7',
        'p3': 'f2eab69'
    }

    @staticmethod
    def generate_uuid() -> str:
        """Generate UUID without hyphens (for traceId and device_id)"""
        return str(uuid.uuid4()).replace('-', '')

    @staticmethod
    def clean_object(obj: Any) -> Any:
        """Remove null, undefined, and empty values from object"""
        if obj is None:
            return None

        if isinstance(obj, list):
            cleaned = [BingxHeaderGenerator.clean_object(item) for item in obj if item is not None]
            return cleaned if cleaned else None

        if isinstance(obj, dict):
            cleaned = {}
            for key, value in obj.items():
                if value is not None:
                    if isinstance(value, (dict, list)):
                        cleaned_value = BingxHeaderGenerator.clean_object(value)
                        if cleaned_value:
                            if isinstance(cleaned_value, list) and len(cleaned_value) > 0:
                                cleaned[key] = cleaned_value
                            elif isinstance(cleaned_value, dict) and len(cleaned_value) > 0:
                                cleaned[key] = cleaned_value
                    else:
                        cleaned[key] = value
            return cleaned if cleaned else None

        return obj

    @staticmethod
    def stable_stringify(obj: Any) -> str:
        """Convert object to stable JSON string with sorted keys"""
        if obj is None:
            return 'null'

        if not isinstance(obj, (dict, list)):
            return json.dumps(obj, separators=(',', ':'))

        if isinstance(obj, list):
            items = [BingxHeaderGenerator.stable_stringify(item) for item in obj]
            return '[' + ','.join(items) + ']'

        # For dictionaries, sort keys
        sorted_items = []
        for key in sorted(obj.keys()):
            value_str = BingxHeaderGenerator.stable_stringify(obj[key])
            sorted_items.append(f'"{key}":{value_str}')

        return '{' + ','.join(sorted_items) + '}'

    @staticmethod
    def get_sign_content_by_object(obj: Any) -> Any:
        """Convert values for signature (numbers to uppercase strings, booleans to strings)"""
        if not isinstance(obj, (dict, list)):
            return obj

        if isinstance(obj, list):
            return [BingxHeaderGenerator.get_sign_content_by_object(item) for item in obj]

        result = {}
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                result[key] = BingxHeaderGenerator.get_sign_content_by_object(value)
            elif isinstance(value, (int, float)):
                # Convert number to uppercase string
                result[key] = str(value).upper()
            elif isinstance(value, bool):
                # Convert boolean to lowercase string
                result[key] = str(value).lower()
            else:
                result[key] = value

        return result

    @staticmethod
    def get_sign_content(timestamp: str, trace_id: str, device_id: str,
                         platform_id: str, app_version: str,
                         params: Optional[Dict] = None) -> str:
        """Generate signature content string"""
        payload_str = "{}"

        if params and isinstance(params, dict) and len(params) > 0:
            # Deep copy the payload
            payload_copy = json.loads(json.dumps(params))

            # Clean the object
            cleaned = BingxHeaderGenerator.clean_object(payload_copy)

            if cleaned:
                # Convert values for signature
                converted = BingxHeaderGenerator.get_sign_content_by_object(cleaned)
                # Create stable string
                payload_str = BingxHeaderGenerator.stable_stringify(converted)

        # Combine secret keys
        secret = f"{BingxHeaderGenerator.ENCRYPTION_KEYS['p1']}{BingxHeaderGenerator.ENCRYPTION_KEYS['p2']}{BingxHeaderGenerator.ENCRYPTION_KEYS['p3']}"

        # Build the final string to hash
        return f"{secret}{timestamp}{trace_id}{device_id}{platform_id}{app_version}{payload_str}"

    @staticmethod
    def sha256(message: str) -> str:
        """Generate SHA256 hash in uppercase hex"""
        return hashlib.sha256(message.encode('utf-8')).hexdigest().upper()

    @staticmethod
    def generate_headers(params: Optional[Dict] = None, **kwargs) -> Dict[str, str]:
        """
        Generate complete headers with signature

        Args:
            params: The request data to be signed
            **kwargs: Override default header values

        Returns:
            Dictionary of headers ready to use in requests
        """
        # Default values
        defaults = {
            'platform_id': 'h5',
            'app_version': '3.9.9',
            'app_site_id': '30003',
            'channel': 'official',
            'app_id': '30004',
            'main_app_id': '10009',
            'lang': 'en',
            'time_zone': str(int(-time.timezone / 3600)),
            'device_brand': 'Windows_Chrome_131.0.0.0'
        }

        # Merge with provided kwargs
        config = {**defaults, **kwargs}

        # Generate dynamic values
        timestamp = str(int(time.time() * 1000))  # Milliseconds
        trace_id = BingxHeaderGenerator.generate_uuid()
        device_id = BingxHeaderGenerator.generate_uuid()

        # Generate signature
        sign_content = BingxHeaderGenerator.get_sign_content(
            timestamp=timestamp,
            trace_id=trace_id,
            device_id=device_id,
            platform_id=config['platform_id'],
            app_version=config['app_version'],
            params=params
        )

        sign = BingxHeaderGenerator.sha256(sign_content)

        # Build headers object
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'platformId': config['platform_id'],
            'appSiteId': config['app_site_id'],
            'channel': config['channel'],
            'reg_channel': config['channel'],
            'app_version': config['app_version'],
            'device_id': device_id,
            'lang': config['lang'],
            'appId': config['app_id'],
            'mainAppId': config['main_app_id'],
            'timeZone': config['time_zone'],
            'device_brand': config['device_brand'],
            'timestamp': timestamp,
            'traceId': trace_id,
            'sign': sign
        }

        return headers
