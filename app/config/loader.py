import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ExchangeConfig:
    """Configuration for a single exchange"""
    name: str
    enabled: bool
    api_url: str
    base_url: str
    proxies: List[str]
    delay: float
    category_mappings: Dict[str, str]

    @property
    def has_proxy(self) -> bool:
        return bool(self.proxies)


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

    @classmethod
    def load(cls, config_dir: str = "config") -> 'AppConfig':
        """Load all configuration files"""
        config_path = Path(config_dir)

        # Load exchange configs
        exchanges_data = cls._load_yaml(config_path / "exchanges.yaml")
        exchanges = {
            name: ExchangeConfig(name=name, **cfg)
            for name, cfg in exchanges_data.items()
        }

        # Load telegram config
        telegram_data = cls._load_yaml(config_path / "telegram.yaml")
        telegram = TelegramConfig(**telegram_data)

        # Load general settings
        general = cls._load_yaml(config_path / "general.yaml")

        return cls(
            exchanges=exchanges,
            telegram=telegram,
            general=general
        )

    @staticmethod
    def _load_yaml(path: Path) -> Dict:
        """Load a YAML file"""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, 'r') as f:
            return yaml.safe_load(f)