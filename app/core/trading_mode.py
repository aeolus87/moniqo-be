"""
Trading Mode Context Management

Manages trading mode (demo/real) context for requests.
Provides context variable storage and retrieval for middleware and dependencies.
"""

from contextvars import ContextVar
from enum import Enum
from typing import Optional
from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.context import TradingMode
from app.core.database import db_provider
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Context variable to store trading mode for current request
_trading_mode_context: ContextVar[Optional[TradingMode]] = ContextVar(
    "trading_mode_context", default=None
)


def set_trading_mode_context(mode: TradingMode) -> None:
    """
    Set trading mode context for current request.
    
    Args:
        mode: Trading mode (DEMO or REAL)
    """
    _trading_mode_context.set(mode)
    logger.debug(f"Set trading mode context to: {mode.value}")


def get_trading_mode_context() -> Optional[TradingMode]:
    """
    Get trading mode context for current request.
    
    Returns:
        TradingMode or None if not set
    """
    return _trading_mode_context.get()


def get_trading_mode_context_or_default() -> TradingMode:
    """
    Get trading mode context, defaulting to DEMO if not set (fail-safe).
    
    Returns:
        TradingMode: Current trading mode (defaults to DEMO)
    """
    mode = _trading_mode_context.get()
    if mode is None:
        logger.debug("Trading mode context not set, defaulting to DEMO (fail-safe)")
        return TradingMode.DEMO
    return mode


async def get_trading_mode_context_dependency() -> TradingMode:
    """
    FastAPI dependency to get trading mode context.
    
    Returns:
        TradingMode: Current trading mode (defaults to DEMO)
    """
    return get_trading_mode_context_or_default()


async def get_database_for_mode(
    trading_mode: TradingMode = Depends(get_trading_mode_context_dependency)
) -> AsyncIOMotorDatabase:
    """
    FastAPI dependency to get database instance for current trading mode.
    
    Args:
        trading_mode: Trading mode from context (injected by dependency)
    
    Returns:
        AsyncIOMotorDatabase: Database instance for current mode
    """
    return db_provider.get_db_for_mode(trading_mode)


async def validate_wallet_mode(
    wallet_id: str,
    expected_mode: TradingMode,
    db: AsyncIOMotorDatabase
) -> bool:
    """
    Validate that a wallet matches the expected trading mode.
    
    Args:
        wallet_id: User wallet ID to validate
        expected_mode: Expected trading mode (DEMO or REAL)
        db: Database instance (can be either, we'll check wallet definition)
    
    Returns:
        bool: True if wallet matches expected mode, False otherwise
        
    Raises:
        HTTPException: If wallet not found or validation fails
    """
    try:
        # Get user_wallet
        user_wallet = await db.user_wallets.find_one({
            "_id": ObjectId(wallet_id),
            "deleted_at": None
        })
        
        if not user_wallet:
            logger.warning(f"Wallet not found: {wallet_id}")
            return False
        
        # Get wallet definition
        wallet_def_id = user_wallet.get("wallet_provider_id")
        if not wallet_def_id:
            logger.warning(f"Wallet definition not found for wallet: {wallet_id}")
            return False
        
        wallet_def = await db.wallets.find_one({
            "_id": ObjectId(wallet_def_id),
            "deleted_at": None
        })
        
        if not wallet_def:
            logger.warning(f"Wallet definition not found: {wallet_def_id}")
            return False
        
        # Determine if wallet is demo
        is_demo_wallet = (
            wallet_def.get("is_demo", False) or
            wallet_def.get("integration_type") == "simulation" or
            "demo" in wallet_def.get("slug", "").lower() or
            user_wallet.get("use_testnet", False)
        )
        
        # Check if wallet mode matches expected mode
        wallet_mode = TradingMode.DEMO if is_demo_wallet else TradingMode.REAL
        
        if wallet_mode != expected_mode:
            logger.warning(
                f"Wallet mode mismatch: wallet_id={wallet_id}, "
                f"wallet_mode={wallet_mode.value}, expected_mode={expected_mode.value}"
            )
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating wallet mode: {e}")
        return False
