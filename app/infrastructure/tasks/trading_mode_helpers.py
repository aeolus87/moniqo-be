"""
Trading Mode Helper Functions for Celery Tasks

Utility functions to determine trading mode from various entities
(position, order, wallet) for use in Celery background tasks.

Author: Moniqo Team
"""

from typing import Optional
from bson import ObjectId

from app.core.context import TradingMode
from app.core.database import db_provider
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def get_trading_mode_from_wallet(user_wallet_id: str) -> TradingMode:
    """
    Determine trading mode from wallet definition.
    
    Args:
        user_wallet_id: User wallet ID
        
    Returns:
        TradingMode: DEMO or REAL (defaults to DEMO for safety)
    """
    if not user_wallet_id:
        return TradingMode.DEMO
    
    try:
        # Use demo database to check wallet (wallets collection is shared)
        db = db_provider.get_db_for_mode(TradingMode.DEMO)
        
        user_wallet = await db.user_wallets.find_one({
            "_id": ObjectId(user_wallet_id),
            "deleted_at": None
        })
        
        if not user_wallet:
            logger.warning(f"Wallet not found: {user_wallet_id}, defaulting to DEMO")
            return TradingMode.DEMO
        
        # Check wallet definition
        wallet_def_id = user_wallet.get("wallet_provider_id")
        if not wallet_def_id:
            logger.warning(f"Wallet definition ID not found for wallet: {user_wallet_id}, defaulting to DEMO")
            return TradingMode.DEMO
        
        wallet_def = await db.wallets.find_one({
            "_id": ObjectId(wallet_def_id),
            "deleted_at": None
        })
        
        if not wallet_def:
            logger.warning(f"Wallet definition not found: {wallet_def_id}, defaulting to DEMO")
            return TradingMode.DEMO
        
        # Determine if demo
        is_demo = (
            wallet_def.get("is_demo", False) or
            wallet_def.get("integration_type") == "simulation" or
            "demo" in wallet_def.get("slug", "").lower() or
            user_wallet.get("use_testnet", False)
        )
        
        return TradingMode.DEMO if is_demo else TradingMode.REAL
        
    except Exception as e:
        logger.error(f"Error determining trading mode from wallet {user_wallet_id}: {e}")
        return TradingMode.DEMO  # Default to demo for safety


async def get_trading_mode_from_position(position_id: str) -> TradingMode:
    """
    Determine trading mode from position's flow/wallet.
    
    Args:
        position_id: Position ID
        
    Returns:
        TradingMode: DEMO or REAL (defaults to DEMO for safety)
    """
    if not position_id:
        return TradingMode.DEMO
    
    try:
        # Try both databases to find position
        db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
        db_real = db_provider.get_db_for_mode(TradingMode.REAL)
        
        # Check demo database first
        position = await db_demo.positions.find_one({
            "_id": ObjectId(position_id),
            "deleted_at": None
        })
        
        if position:
            # Found in demo DB - check wallet to confirm
            user_wallet_id = position.get("user_wallet_id")
            if user_wallet_id:
                return await get_trading_mode_from_wallet(str(user_wallet_id))
            # No wallet - check flow
            flow_id = position.get("flow_id")
            if flow_id:
                return await get_trading_mode_from_flow(str(flow_id))
            return TradingMode.DEMO
        
        # Check real database
        position = await db_real.positions.find_one({
            "_id": ObjectId(position_id),
            "deleted_at": None
        })
        
        if position:
            # Found in real DB - check wallet to confirm
            user_wallet_id = position.get("user_wallet_id")
            if user_wallet_id:
                return await get_trading_mode_from_wallet(str(user_wallet_id))
            # No wallet - check flow
            flow_id = position.get("flow_id")
            if flow_id:
                return await get_trading_mode_from_flow(str(flow_id))
            return TradingMode.REAL
        
        logger.warning(f"Position not found: {position_id}, defaulting to DEMO")
        return TradingMode.DEMO
        
    except Exception as e:
        logger.error(f"Error determining trading mode from position {position_id}: {e}")
        return TradingMode.DEMO  # Default to demo for safety


async def get_trading_mode_from_order(order_id: str) -> TradingMode:
    """
    Determine trading mode from order's flow/wallet.
    
    Args:
        order_id: Order ID
        
    Returns:
        TradingMode: DEMO or REAL (defaults to DEMO for safety)
    """
    if not order_id:
        return TradingMode.DEMO
    
    try:
        # Try both databases to find order
        db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
        db_real = db_provider.get_db_for_mode(TradingMode.REAL)
        
        # Check demo database first
        order = await db_demo.orders.find_one({
            "_id": ObjectId(order_id),
            "deleted_at": None
        })
        
        if order:
            # Found in demo DB - check wallet to confirm
            user_wallet_id = order.get("user_wallet_id")
            if user_wallet_id:
                return await get_trading_mode_from_wallet(str(user_wallet_id))
            # No wallet - check flow
            flow_id = order.get("flow_id")
            if flow_id:
                return await get_trading_mode_from_flow(str(flow_id))
            return TradingMode.DEMO
        
        # Check real database
        order = await db_real.orders.find_one({
            "_id": ObjectId(order_id),
            "deleted_at": None
        })
        
        if order:
            # Found in real DB - check wallet to confirm
            user_wallet_id = order.get("user_wallet_id")
            if user_wallet_id:
                return await get_trading_mode_from_wallet(str(user_wallet_id))
            # No wallet - check flow
            flow_id = order.get("flow_id")
            if flow_id:
                return await get_trading_mode_from_flow(str(flow_id))
            return TradingMode.REAL
        
        logger.warning(f"Order not found: {order_id}, defaulting to DEMO")
        return TradingMode.DEMO
        
    except Exception as e:
        logger.error(f"Error determining trading mode from order {order_id}: {e}")
        return TradingMode.DEMO  # Default to demo for safety


async def get_trading_mode_from_flow(flow_id: str) -> TradingMode:
    """
    Determine trading mode from flow's wallet.
    
    Args:
        flow_id: Flow ID
        
    Returns:
        TradingMode: DEMO or REAL (defaults to DEMO for safety)
    """
    if not flow_id:
        return TradingMode.DEMO
    
    try:
        # Try both databases to find flow
        db_demo = db_provider.get_db_for_mode(TradingMode.DEMO)
        db_real = db_provider.get_db_for_mode(TradingMode.REAL)
        
        # Check demo database first
        flow = await db_demo.flows.find_one({
            "_id": ObjectId(flow_id),
            "deleted_at": None
        })
        
        if not flow:
            # Check real database
            flow = await db_real.flows.find_one({
                "_id": ObjectId(flow_id),
                "deleted_at": None
            })
        
        if not flow:
            logger.warning(f"Flow not found: {flow_id}, defaulting to DEMO")
            return TradingMode.DEMO
        
        # Get wallet from flow config
        config = flow.get("config", {})
        wallet_id_config = str(config.get("user_wallet_id", ""))
        
        if wallet_id_config:
            return await get_trading_mode_from_wallet(wallet_id_config)
        
        # No wallet in config - default to demo for safety
        logger.warning(f"Flow {flow_id} has no wallet_id in config, defaulting to DEMO")
        return TradingMode.DEMO
        
    except Exception as e:
        logger.error(f"Error determining trading mode from flow {flow_id}: {e}")
        return TradingMode.DEMO  # Default to demo for safety
