import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import re


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

        # Load shared configurations first
        shared_configs = cls._load_shared_configs(config_path)

        # Load exchange configs with shared config resolution
        exchanges_data = cls._load_yaml_with_references(
            config_path / "exchanges.yaml", 
            shared_configs
        )
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

    @staticmethod
    def _load_shared_configs(config_path: Path) -> Dict[str, Any]:
        """Load all shared configuration files"""
        shared_configs = {}
        shared_dir = config_path / "shared"
        
        if shared_dir.exists():
            for yaml_file in shared_dir.glob("*.yaml"):
                config_name = yaml_file.stem
                shared_configs[config_name] = AppConfig._load_yaml(yaml_file)
        
        return shared_configs

    @staticmethod
    def _load_yaml_with_references(path: Path, shared_configs: Dict[str, Any]) -> Dict:
        """Load a YAML file and resolve references to shared configurations"""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, 'r') as f:
            content = f.read()

        # Resolve references in the YAML content
        resolved_content = AppConfig._resolve_references(content, shared_configs)
        
        return yaml.safe_load(resolved_content)

    @staticmethod
    def _resolve_references(content: str, shared_configs: Dict[str, Any]) -> str:
        """Resolve references like DEFAULT_HEADERS to actual values from shared configs"""
        # Pattern to match references like DEFAULT_HEADERS
        reference_pattern = r'^(\s*)(\w+):\s*(\w+)$'
        
        lines = content.split('\n')
        resolved_lines = []
        
        for line in lines:
            match = re.match(reference_pattern, line)
            if match:
                indent, key, reference = match.groups()
                
                # Check if the reference exists in shared configs
                if reference in shared_configs:
                    # Convert the shared config to YAML format
                    import yaml
                    shared_yaml = yaml.dump(shared_configs[reference], default_flow_style=False)
                    # Indent the shared config content to match the original indentation
                    indented_shared = '\n'.join(
                        indent + shared_line if shared_line.strip() else shared_line
                        for shared_line in shared_yaml.split('\n')
                        if shared_line.strip()  # Skip empty lines
                    )
                    resolved_lines.append(f"{indent}{key}:")
                    resolved_lines.append(indented_shared)
                else:
                    # Keep original line if reference not found
                    resolved_lines.append(line)
            else:
                resolved_lines.append(line)
        
        return '\n'.join(resolved_lines)