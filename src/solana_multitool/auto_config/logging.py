"""
logging_config.py

Centralized logging configuration for the solana_multitool project.
"""

import logging
import logging.config
from pathlib import Path
from datetime import datetime
from typing import Optional

class Logger:
    """
    LoggerConfig object for centralized logging setup and access.
    """
    def __init__(self, log_level: str = 'INFO', console_output: bool = True, log_dir: Path | str | None = None):
        self.log_level = log_level
        self.console_output = console_output
        self.log_dir = log_dir
        self.logger = None
        self.log_path = None
        self.setup_logging()

    def find_project_root(self, *markers: str) -> Optional[Path]:
        current_path = Path(__file__).resolve()
        for parent in current_path.parents:
            for marker in markers:
                if (parent / marker).exists():
                    return parent
        return None

    def setup_logging(self):
        if self.log_dir is None:
            project_root = self.find_project_root('.git', 'pyrightconfig.json', 'README.md', 'src')
            if not project_root:
                raise FileNotFoundError(
                    "Could not find the project root. Make sure a marker like '.git' or 'pyrightconfig.json' exists in the root."
                )
            self.log_dir = project_root / "logs"

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_filename = f"solana_multitool_{timestamp}.log"
        self.log_path = Path(self.log_dir) / log_filename

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        handlers = {
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'file_formatter',
                'filename': self.log_path,
                'encoding': 'utf-8',
            }
        }
        root_handlers = ['file']

        if self.console_output:
            handlers['console'] = {
                'class': 'logging.StreamHandler',
                'formatter': 'console_formatter',
                'level': self.log_level,
            }
            root_handlers.append('console')

        LOGGING_CONFIG = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'file_formatter': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s',
                },
                'console_formatter': {
                    'format': '%(levelname)s - %(message)s',
                },
            },
            'handlers': handlers,
            'root': {
                'level': self.log_level,
                'handlers': root_handlers,
            },
        }

        logging.config.dictConfig(LOGGING_CONFIG)
        self.logger = logging.getLogger()
        self.logger.info(f"Logging configured. Log file will be created at: {self.log_path}")

    def get_logger(self, name: str) -> logging.Logger:
        if name:
            return logging.getLogger(name)
        # Always return a Logger, fallback to root logger if self.logger is None
        return self.logger if self.logger is not None else logging.getLogger()

logging_config = Logger()
