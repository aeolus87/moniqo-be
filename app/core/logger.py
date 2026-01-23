"""
Clean, Colored Logging Configuration

Provides structured, readable log output with colors and timestamps.
Replaces the default FastAPI/uvicorn logging mess.

Usage:
    from app.core.logger import get_logger
    logger = get_logger(__name__)

    # In main.py:
    from app.core.logger import setup_logging
    setup_logging()
"""

import logging
import sys
from typing import Optional
from datetime import datetime, timezone


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and clean structure"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',      # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        # Add timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        # Add colors
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']

        # Clean module name (remove app. prefix)
        module_name = record.name.replace('app.', '') if record.name.startswith('app.') else record.name

        # Format: [TIMESTAMP] LEVEL [MODULE] MESSAGE
        formatted_message = f"{level_color}[{timestamp}] {record.levelname:<8} [{module_name:<20}] {record.getMessage()}{reset_color}"

        # Add exception info if present
        if record.exc_info:
            formatted_message += f"\n{self.formatException(record.exc_info)}"

        return formatted_message


def setup_logging(
    level: str = "INFO",
    format_type: str = "colored",
    log_file: Optional[str] = None
) -> None:
    """
    Setup clean logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "colored" for console with colors, "json" for structured
        log_file: Optional file path to also log to file
    """
    # Clear ALL existing handlers first to prevent duplicates from Uvicorn
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Set root logger level
    root_logger.setLevel(numeric_level)

    # Create console handler with colored formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if format_type == "colored":
        formatter = ColoredFormatter()
    elif format_type == "simple":
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Default structured format
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party logs
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('motor').setLevel(logging.WARNING)
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)  # Hide access logs
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)   # Let our logger handle errors

    # Set uvicorn to use our logger and prevent duplicates
    uvicorn_logger = logging.getLogger('uvicorn')
    uvicorn_logger.handlers = []
    uvicorn_logger.addHandler(console_handler)
    uvicorn_logger.propagate = False

    # Prevent duplicate logs from root logger and other FastAPI components
    logging.getLogger().propagate = False
    logging.getLogger('fastapi').propagate = False
    logging.getLogger('starlette').propagate = False


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Convenience function for quick setup
def setup_development_logging():
    """Setup logging for development with colored output"""
    setup_logging(level="INFO", format_type="colored")


def setup_production_logging(log_file: str = "app.log"):
    """Setup logging for production with file output"""
    setup_logging(level="WARNING", format_type="simple", log_file=log_file)