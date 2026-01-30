"""
Logging configuration for the application.

Sets up logging with file rotation and appropriate levels for different environments.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """
    Configure application logging.
    
    Sets up logging with:
    - Console output (stdout)
    - File output with rotation
    - Appropriate log levels based on environment
    - Formatted log messages
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("moniqo")
    
    # Set log level from settings (default to INFO if settings not loaded)
    log_level_str = settings.LOG_LEVEL.upper() if settings else "INFO"
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    simple_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if settings:
        try:
            # Ensure log directory exists
            log_file_path = Path(settings.LOG_FILE_PATH)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                filename=settings.LOG_FILE_PATH,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,  # Keep 5 backup files
                encoding="utf-8"
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.warning(f"Failed to setup file logging: {str(e)}")
    
    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__ of the module)
        
    Returns:
        logging.Logger: Logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("User created successfully", extra={"user_id": "123"})
    """
    return logging.getLogger(f"moniqo.{name}")


# Initialize logging on import
app_logger = setup_logging()

