import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import copy


@dataclass
class CategoryMapping:
    """Category mapping configuration"""
    original_ids: List[str]
    show_name: str
    internal_name: str
    title_regex: Optional[str] = None

    def to_dict(self):
        return {
            'original_ids': self.original_ids,
            'show_name': self.show_name,
            'internal_name': self.internal_name
        }


@dataclass
class RequestConfig:
    """Request configuration for an exchange"""
    api_url: str
    method: str = "get"
    header_profile: str = "basic"
    proxy_pool: str = "rotating_main"
    rate_limit_profile: str = "moderate"
    headers_override: Dict[str, str] = field(default_factory=dict)
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    poll_interval: int = 60
    navigation_id_refresh: Optional[int] = None


@dataclass
class ExchangeConfig:
    """Configuration for a single exchange"""
    name: str
    enabled: bool
    request: RequestConfig
    monitoring: MonitoringConfig
    categories: List[CategoryMapping]
    patterns: List[str]

    # Resolved configurations
    headers: Dict[str, str] = field(default_factory=dict)
    proxies: List[str] = field(default_factory=list)
    poll_interval: float = 1.0

    @property
    def api_url(self) -> str:
        return self.request.api_url

    @property
    def has_proxy(self) -> bool:
        return bool(self.proxies)


@dataclass
class SharedConfig:
    """Shared configuration resources"""
    headers: Dict[str, Dict[str, str]]
    proxies: Dict[str, Any]
    rate_limits: Dict[str, Any]


@dataclass
class TelegramConfig:
    """Telegram notification configuration"""
    bot_token: str
    chat_id: int
    thread_mappings: List[Dict[str, Any]]
    default_thread: int


@dataclass
class AppConfig:
    """Main application configuration"""
    exchanges: Dict[str, ExchangeConfig]
    telegram: TelegramConfig
    general: Dict[str, Any]
    shared: SharedConfig

    @classmethod
    def load(cls, config_dir: str = "config") -> 'AppConfig':
        """Load all configuration files"""
        config_path = Path(config_dir)

        # Load shared configurations
        shared = cls._load_shared_configs(config_path)

        # Load exchange defaults
        defaults = cls._load_yaml(config_path / "exchanges" / "defaults.yaml")

        # Load all exchange configs
        exchanges = cls._load_exchanges(config_path, defaults, shared)

        # Load telegram config
        telegram_data = cls._load_yaml(config_path / "telegram.yaml")
        telegram = TelegramConfig(**telegram_data)

        # Load general settings
        general = cls._load_yaml(config_path / "general.yaml")

        return cls(
            exchanges=exchanges,
            telegram=telegram,
            general=general,
            shared=shared
        )

    @classmethod
    def _load_shared_configs(cls, config_path: Path) -> SharedConfig:
        """Load shared configuration files"""
        shared_dir = config_path / "shared"

        # Load headers
        headers_file = shared_dir / "headers.yaml"
        headers_data = cls._load_yaml(headers_file) if headers_file.exists() else {"profiles": {}}

        # Load proxies
        proxies_file = shared_dir / "proxies.yaml"
        proxies_data = cls._load_yaml(proxies_file) if proxies_file.exists() else {"pools": {}}

        # Load rate limits (if exists)
        rate_limits_file = shared_dir / "rate_limits.yaml"
        rate_limits_data = cls._load_yaml(rate_limits_file) if rate_limits_file.exists() else {"profiles": {}}

        return SharedConfig(
            headers=headers_data.get("profiles", {}),
            proxies=proxies_data.get("pools", {}),
            rate_limits=rate_limits_data.get("profiles", {})
        )

    @classmethod
    def _load_exchanges(cls, config_path: Path, defaults: Dict, shared: SharedConfig) -> Dict[str, ExchangeConfig]:
        """Load all exchange configurations"""
        exchanges_dir = config_path / "exchanges"
        exchanges = {}

        # Load each exchange YAML file
        for yaml_file in exchanges_dir.glob("*.yaml"):
            if yaml_file.name == "defaults.yaml":
                continue

            exchange_name = yaml_file.stem
            exchange_data = cls._load_yaml(yaml_file)

            # Skip if empty or invalid
            if not exchange_data or exchange_name not in exchange_data:
                continue

            # Get exchange-specific config
            config = exchange_data[exchange_name]

            # Merge with defaults
            merged_config = cls._merge_configs(defaults.get("defaults", {}), config)

            # Parse exchange config
            exchange_config = cls._parse_exchange_config(
                exchange_name,
                merged_config,
                shared
            )

            if exchange_config:
                exchanges[exchange_name] = exchange_config

        return exchanges

    @classmethod
    def _parse_exchange_config(cls, name: str, config: Dict, shared: SharedConfig) -> Optional[ExchangeConfig]:
        """Parse individual exchange configuration"""
        try:
            # Parse request config
            request_data = config.get("request", {})
            request_config = RequestConfig(
                api_url=request_data.get("api_url", ""),
                method=request_data.get("method", "get"),
                header_profile=request_data.get("header_profile", "basic"),
                proxy_pool=request_data.get("proxy_pool", "rotating_main"),
                rate_limit_profile=request_data.get("rate_limit_profile", "moderate"),
                headers_override=request_data.get("headers_override", {}),
                kwargs=request_data.get("kwargs", {})
            )

            # Parse monitoring config
            monitoring_data = config.get("monitoring", {})
            monitoring_config = MonitoringConfig(
                poll_interval=monitoring_data.get("poll_interval", 60),
                navigation_id_refresh=monitoring_data.get("navigation_id_refresh")
            )

            # Parse categories
            categories = []
            for cat_data in config.get("categories", []):
                categories.append(CategoryMapping(
                    original_ids=cat_data.get("original_ids", []),
                    show_name=cat_data.get("show_name", ""),
                    internal_name=cat_data.get("internal_name", "other"),
                    title_regex=cat_data.get("title_regex", "")
                ))

            # Resolve headers from profile
            headers = {}
            if request_config.header_profile in shared.headers:
                headers = shared.headers[request_config.header_profile].copy()
            # Apply overrides
            headers.update(request_config.headers_override)

            # Resolve proxies from pool
            proxies = []
            if request_config.proxy_pool in shared.proxies:
                pool_config = shared.proxies[request_config.proxy_pool]
                proxies = pool_config.get("proxies", [])

            # Resolve rate limit (delay)
            delay = cls._get_delay_from_rate_limit(
                request_config.rate_limit_profile,
                shared.rate_limits
            )

            return ExchangeConfig(
                name=name,
                enabled=config.get("enabled", False),
                request=request_config,
                monitoring=monitoring_config,
                categories=categories,
                headers=headers,
                proxies=proxies,
                poll_interval=delay,
                patterns=config.get("patterns", [])
            )

        except Exception as e:
            print(f"Error parsing config for {name}: {e}")
            return None

    @classmethod
    def _get_delay_from_rate_limit(cls, profile: str, rate_limits: Dict) -> float:
        """Convert rate limit profile to delay"""
        rate_limit_delays = {
            "strict": 5.0,
            "moderate": 2.0,
            "relaxed": 1.0,
            "aggressive": 0.5
        }

        # Check if profile exists in rate_limits config
        if profile in rate_limits:
            rps = rate_limits[profile].get("requests_per_second", 1)
            return 1.0 / rps if rps > 0 else 1.0

        # Fallback to predefined delays
        return rate_limit_delays.get(profile, 1.0)

    @classmethod
    def _merge_configs(cls, defaults: Dict, specific: Dict) -> Dict:
        """Deep merge defaults with specific config"""
        result = copy.deepcopy(defaults)

        for key, value in specific.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                result[key] = cls._merge_configs(result[key], value)
            else:
                # Override with specific value
                result[key] = value

        return result

    @staticmethod
    def _load_yaml(path: Path) -> Dict:
        """Load a YAML file"""
        if not path.exists():
            return {}

        with open(path, 'r') as f:
            return yaml.safe_load(f) or {}