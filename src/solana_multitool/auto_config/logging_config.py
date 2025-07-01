import logging
import logging.config
from pathlib import Path
from datetime import datetime

def setup_logging(
    file_log_level: str = 'INFO',
    console_log_level: str = 'ERROR',
    log_dir: Path | str | None = None
):
    """
    Configures logging for the entire application.
    The RichHandler for the console will not interfere with Rich spinners.
    """
    project_root = Path(__file__).resolve().parents[3]
    log_dir = log_dir or (project_root / "logs")
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = log_path / f"solana_multitool_{timestamp}.log"

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'file_formatter': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
            'console_formatter': {
                'format': '%(message)s',
            },
        },
        'handlers': {
            # This handler uses Rich and will not break spinners
            'console': {
                'class': 'rich.logging.RichHandler',
                'level': console_log_level.upper(),
                'formatter': 'console_formatter',
            },
            # This handler writes all logs to a file
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': file_log_level.upper(),
                'formatter': 'file_formatter',
                'filename': log_filename,
                'maxBytes': 10*1024*1024,
                'backupCount': 5,
                'encoding': 'utf-8',
            },
        },
        'root': {
            'level': 'DEBUG', # Let all messages pass to handlers
            'handlers': ['console', 'file'],
        },
    }

    logging.config.dictConfig(LOGGING_CONFIG)
    logging.getLogger().info(f"Logging configured. Log file at: {log_filename}")

setup_logging()

logger = logging.getLogger(__name__)
