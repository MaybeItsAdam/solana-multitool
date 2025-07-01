import os
from solana_multitool.auto_config.logging_config import logger
from pathlib import Path
import logging
from typing import Optional
from dotenv import load_dotenv, find_dotenv



def load_env_file() -> None:
    """
        Load environment variables from a .env file using the python-dotenv library.

        This function is robust and handles path resolution automatically, making it
        suitable for use in various parts of a project.

        Args:
            env_file_path: Optional path to the .env file. If None, it automatically
                           searches for a '.env' file by traversing up the directory tree.

        Returns:
            True if a .env file was found and loaded, False otherwise.
        """
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / "config" / ".env"

    if not env_path or not Path(env_path).exists():
        print("No .env file found to load.")

    try:
        was_loaded = load_dotenv(dotenv_path=env_path, override=True)
        if not was_loaded:
            print(f"Environment variables NOT LOADED from: {env_path}")
    except Exception as e:
        print(f"Could not load .env file from {env_path}: {e}")


class Config:
    def __init__(self) -> None:
        # Load .env file on initialization
        load_env_file()

        # Solana RPC Configuration
        self.solana_rpc_url = self._get_env_var(
            'SOLANA_RPC_URL',
            default='https://api.mainnet-beta.solana.com'
        )

        fallback_url = self._get_env_var('FALLBACK_RPC_URL')
        self.fallback_rpc_url: Optional[str] = fallback_url if fallback_url else None

        # Rate Limiting Configuration
        try:
            rate_limit_str = self._get_env_var('MAX_REQUESTS_PER_SECOND', default='8')
            self.max_requests_per_second = int(rate_limit_str)
        except (ValueError, TypeError):
            print(f"⚠️  Warning: Invalid MAX_REQUESTS_PER_SECOND value. Using default: 8")
            self.max_requests_per_second = 8

        # Logging Configuration
        log_level_str = self._get_env_var('LOG_LEVEL', default='ERROR').upper()

        # Map string to logging level
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }

        if log_level_str not in level_map:
            print(f"⚠️  Warning: Invalid LOG_LEVEL: {log_level_str}. Using ERROR.")
            self.log_level = logging.ERROR
        else:
            self.log_level = level_map[log_level_str]

        # Validate configuration
        self._validate_config()

    def _get_env_var(self, key: str, default: str = '') -> str:
        """
        Args:
            key: Environment variable key
            default: Default value if not set
        """

        value = os.environ.get(key)
        return value if value is not None else default

    def _validate_config(self) -> None:
        """Validate configuration values with fallbacks for invalid values."""
        # Validate RPC URL
        if not self.solana_rpc_url or not self.solana_rpc_url.startswith('http'):
            print(f"⚠️  Warning: Invalid SOLANA_RPC_URL: {self.solana_rpc_url}")
            print("   Using default public RPC endpoint.")
            self.solana_rpc_url = 'https://api.mainnet-beta.solana.com'

        # Validate rate limiting
        if self.max_requests_per_second <= 0:
            print(f"⚠️  Warning: Invalid MAX_REQUESTS_PER_SECOND: {self.max_requests_per_second}")
            print("   Using default rate limit of 8 req/sec.")
            self.max_requests_per_second = 8

        # Check if using public RPC (warn about rate limits)
        if 'api.mainnet-beta.solana.com' in self.solana_rpc_url:
            print("⚠️  Warning: Using public Solana RPC. Consider using a dedicated RPC provider for better performance.")

    def get_rpc_url(self, use_fallback: bool = False) -> str:
        if use_fallback:
            if self.fallback_rpc_url is not None:
                return self.fallback_rpc_url
            raise ValueError("A fallback RPC URL was requested, but none is configured.")

        return self.solana_rpc_url

    def is_quicknode(self) -> bool:
        """Check if the configured RPC is a QuickNode endpoint."""
        return 'quiknode' in self.solana_rpc_url.lower()

    def get_provider_key(self) -> str:
        """Get provider key for transaction metadata."""
        if self.is_quicknode():
            return "quicknode"
        elif 'alchemy' in self.solana_rpc_url.lower():
            return "alchemy"
        elif 'helius' in self.solana_rpc_url.lower():
            return "helius"
        elif 'api.mainnet-beta.solana.com' in self.solana_rpc_url:
            return "public_rpc"
        else:
            return "custom_rpc"

    def _mask_url(self, url: str) -> str:
        """Mask sensitive parts of URL for display."""
        if not url:
            return "None"

        # last part might contain API key
        parts = url.split('/')
        if len(parts) >= 4:
            # Check if the last non-empty part looks like an API key
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] and len(parts[i]) > 10:  # Likely an API key
                    parts[i] = '*' * 8
                    break

        return '/'.join(parts)

    def print_config(self) -> None:
        """Print current configuration (excluding sensitive data)."""
        print("Solana Multitool Configuration:")
        print(f"   RPC URL: {self._mask_url(self.solana_rpc_url)}")
        if self.fallback_rpc_url is not None:
            print(f"   Fallback RPC: {self._mask_url(self.fallback_rpc_url)}")
        print(f"   Rate Limit: {self.max_requests_per_second} req/sec")
        print(f"   Log Level: {logging.getLevelName(self.log_level)}")
        print(f"   Provider: {self.get_provider_key()}")

config = Config()

# Access the config
def get_solana_rpc_url(use_fallback: bool = False) -> str:
    """Get the configured Solana RPC URL."""
    return config.get_rpc_url(use_fallback)

def get_max_requests_per_second() -> int:
    """Get the configured rate limit."""
    return config.max_requests_per_second

def get_log_level() -> int:
    """Get the configured log level."""
    return config.log_level

def get_provider_key() -> str:
    """Get the provider key for metadata."""
    return config.get_provider_key()

# Show configuration on import
config.print_config()
