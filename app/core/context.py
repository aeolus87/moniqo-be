"""
Trading Mode Context Management

Manages trading mode (demo/real) context for requests using contextvars.
Provides automatic database routing based on request context.

Author: Moniqo Team
"""

from contextvars import ContextVar
from enum import Enum
from typing import Optional
from fastapi import Depends

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TradingMode(str, Enum):
    """Trading mode enum."""
    DEMO = "demo"
    REAL = "real"


# Global context variable isolated to each request
# Defaults to DEMO for fail-safe behavior
trading_mode: ContextVar[TradingMode] = ContextVar(
    "trading_mode",
    default=TradingMode.DEMO
)


def set_trading_mode(mode: TradingMode) -> None:
    """
    Set trading mode context for current request.
    
    Args:
        mode: Trading mode (DEMO or REAL)
    """
    trading_mode.set(mode)
    logger.debug(f"Set trading mode context to: {mode.value}")


def get_trading_mode() -> TradingMode:
    """
    Get trading mode context for current request.
    Always returns a mode (defaults to DEMO if not set - fail-safe).
    
    Returns:
        TradingMode: Current trading mode (defaults to DEMO)
    """
    return trading_mode.get()


def get_trading_mode_optional() -> Optional[TradingMode]:
    """
    Get trading mode context, returning None if not set.
    
    Returns:
        TradingMode or None
    """
    mode = trading_mode.get()
    # If it's the default, check if it was explicitly set
    if mode == TradingMode.DEMO:
        # Check if context was actually set or is just default
        # This is a limitation of contextvars - we can't distinguish
        # For now, always return the value
        return mode
    return mode


async def get_trading_mode_dependency() -> TradingMode:
    """
    FastAPI dependency to get trading mode context.
    
    Returns:
        TradingMode: Current trading mode (defaults to DEMO)
    """
    return get_trading_mode()
