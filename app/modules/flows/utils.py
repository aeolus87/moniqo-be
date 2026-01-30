"""
Flow Utilities

Shared utility functions for flow operations.

Author: Moniqo Team
"""

from typing import Optional, Any, Dict, Tuple
from decimal import Decimal
from enum import Enum
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.logger import get_logger

logger = get_logger(__name__)


def to_object_id(value: Optional[str]) -> Optional[ObjectId]:
    """Convert string to ObjectId when possible."""
    if not value:
        return None
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def to_serializable(value: Any) -> Any:
    """Convert values (Decimal, Enum, nested structures) to Mongo-safe types."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: to_serializable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_serializable(item) for item in value]
    return value


def to_response_payload(value: Any) -> Any:
    """Convert values to API-safe types (includes ObjectId stringification)."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: to_response_payload(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_response_payload(item) for item in value]
    return value


async def get_or_create_demo_user(db: AsyncIOMotorDatabase) -> Optional[str]:
    """
    Get or create a demo user for demo mode positions.
    
    Returns:
        str: Demo user ID, or None if creation fails
    """
    try:
        # Try to find existing demo user by email
        auth = await db["auth"].find_one({"email": "demo@moniqo.com", "is_deleted": False})
        if auth:
            user = await db["users"].find_one({"auth_id": auth["_id"], "is_deleted": False})
            if user:
                logger.info(f"Found existing demo user: {user['_id']}")
                return str(user["_id"])
        
        # Create demo user if not found
        from app.core.security import hash_password
        import warnings
        
        # Suppress bcrypt version warning (non-critical)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning, module="passlib")
            # Create auth record
            auth_data = {
                "email": "demo@moniqo.com",
                "password_hash": hash_password("demo_password_not_used"),
                "is_verified": True,
                "is_active": True,
                "is_deleted": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            auth_result = await db["auth"].insert_one(auth_data)
            auth_id = auth_result.inserted_id
            
            # Create user record
            user_data = {
                "auth_id": auth_id,
                "first_name": "Demo",
                "last_name": "User",
                "is_deleted": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            user_result = await db["users"].insert_one(user_data)
            user_id = str(user_result.inserted_id)
            
            logger.info(f"Created demo user: {user_id}")
            return user_id
    except Exception as e:
        logger.error(f"Failed to get or create demo user: {e}")
        return None


def resolve_order_quantity(
    action: str,
    current_price: Decimal,
    base_balance: Optional[Decimal],
    quote_balance: Optional[Decimal],
    order_quantity: Optional[Decimal],
    order_size_usd: Optional[Decimal],
    order_size_percent: Optional[Decimal],
    default_balance_percent: Decimal,
    ai_position_size_usd: Optional[Decimal] = None,
    ai_position_size_percent: Optional[Decimal] = None,
) -> Tuple[Decimal, Dict[str, Any]]:
    """
    Resolve order quantity using balances and sizing rules.
    
    Priority: AI-provided sizing > explicit order_quantity > order_size_usd/percent > default_balance_percent
    
    Args:
        action: Trading action ("buy" or "sell")
        current_price: Current market price
        base_balance: Base asset balance
        quote_balance: Quote asset balance
        order_quantity: Explicit quantity (highest priority if provided)
        order_size_usd: USD size from config
        order_size_percent: Percent size from config
        default_balance_percent: Default balance percent fallback
        ai_position_size_usd: AI-provided position size in USD (optional)
        ai_position_size_percent: AI-provided position size as percent (optional)
    
    Returns:
        Tuple of (quantity, sizing_metadata)
    """
    if current_price <= 0:
        raise Exception("Cannot resolve quantity without a valid current price")

    sizing_meta: Dict[str, Any] = {
        "base_balance": float(base_balance) if base_balance is not None else None,
        "quote_balance": float(quote_balance) if quote_balance is not None else None,
    }

    # Priority 1: Explicit order_quantity (highest priority)
    if order_quantity is not None:
        sizing_meta["sizing_method"] = "explicit_quantity"
        return order_quantity, sizing_meta

    # Priority 2: AI-provided sizing (AI AUTONOMY)
    if ai_position_size_usd is not None:
        sizing_meta["sizing_method"] = "ai_usd"
        sizing_meta["ai_position_size_usd"] = float(ai_position_size_usd)
        if action == "buy":
            if quote_balance is None:
                raise Exception("Quote balance unavailable for buy sizing")
            # Cap AI sizing to available balance
            order_size_usd = min(ai_position_size_usd, quote_balance)
            sizing_meta["order_size_usd"] = float(order_size_usd)
            return order_size_usd / current_price, sizing_meta
        else:  # sell
            if base_balance is None:
                raise Exception("Base balance unavailable for sell sizing")
            quantity = ai_position_size_usd / current_price
            return min(quantity, base_balance), sizing_meta
    
    if ai_position_size_percent is not None:
        sizing_meta["sizing_method"] = "ai_percent"
        sizing_meta["ai_position_size_percent"] = float(ai_position_size_percent)
        if action == "buy":
            if quote_balance is None:
                raise Exception("Quote balance unavailable for buy sizing")
            order_size_usd = (ai_position_size_percent / Decimal("100")) * quote_balance
            order_size_usd = min(order_size_usd, quote_balance)
            sizing_meta["order_size_usd"] = float(order_size_usd)
            return order_size_usd / current_price, sizing_meta
        else:  # sell
            if base_balance is None:
                raise Exception("Base balance unavailable for sell sizing")
            quantity = (ai_position_size_percent / Decimal("100")) * base_balance
            return min(quantity, base_balance), sizing_meta

    # Priority 3: Config-based sizing (fallback)
    if action == "buy":
        if quote_balance is None:
            raise Exception("Quote balance unavailable for buy sizing")
        if order_size_percent is not None:
            order_size_usd = (order_size_percent / Decimal("100")) * quote_balance
            sizing_meta["sizing_method"] = "config_percent"
        elif order_size_usd is not None:
            sizing_meta["sizing_method"] = "config_usd"
        else:
            order_size_usd = (default_balance_percent / Decimal("100")) * quote_balance
            sizing_meta["sizing_method"] = "default_percent"
        order_size_usd = min(order_size_usd, quote_balance)
        sizing_meta["order_size_usd"] = float(order_size_usd)
        return order_size_usd / current_price, sizing_meta

    if base_balance is None:
        raise Exception("Base balance unavailable for sell sizing")
    if order_size_percent is not None:
        sizing_meta["sizing_method"] = "config_percent"
        quantity = (order_size_percent / Decimal("100")) * base_balance
    elif order_size_usd is not None:
        sizing_meta["sizing_method"] = "config_usd"
        quantity = order_size_usd / current_price
    else:
        sizing_meta["sizing_method"] = "default_percent"
        quantity = (default_balance_percent / Decimal("100")) * base_balance

    return min(quantity, base_balance), sizing_meta


def resolve_demo_force_action(
    analysis_action: str,
    signal_data: Optional[Dict[str, Any]],
    config: Dict[str, Any],
) -> Tuple[str, str]:
    """Resolve a forced action for demo mode when analysis returns hold."""
    if analysis_action in {"buy", "sell"}:
        return analysis_action, "Analysis action used for demo execution."

    configured_action = config.get("demo_force_action")
    if configured_action in {"buy", "sell"}:
        return configured_action, "demo_force_action override applied."

    classification = (signal_data or {}).get("classification")
    if classification in {"bullish", "very_bullish"}:
        return "buy", "Signal classification bullish; forced buy."
    if classification in {"bearish", "very_bearish"}:
        return "sell", "Signal classification bearish; forced sell."

    return "buy", "No actionable signal; defaulting forced action to buy."


def resolve_leverage(
    execution_config: Dict[str, Any],
    wallet_capabilities: Dict[str, Any],
    default_leverage: int = 1
) -> int:
    """
    Resolve leverage from config with validation.
    
    Args:
        execution_config: Flow execution config
        wallet_capabilities: Wallet capabilities (max_leverage, etc.)
        default_leverage: Default if not specified
    
    Returns:
        Validated leverage (1-max_leverage)
    
    Example:
        leverage = resolve_leverage(
            execution_config={"leverage": 10},
            wallet_capabilities={"max_leverage": 20},
            default_leverage=1
        )
        # Returns: 10
    """
    leverage = execution_config.get("leverage", default_leverage)
    
    # Ensure leverage is an integer
    try:
        leverage = int(leverage)
    except (TypeError, ValueError):
        logger.warning(f"Invalid leverage value: {leverage}, using default: {default_leverage}")
        leverage = default_leverage
    
    # Get max leverage from wallet capabilities (default 20 for Hyperliquid)
    max_leverage = wallet_capabilities.get("max_leverage", 20)
    
    # Clamp leverage between 1 and max_leverage
    leverage = max(1, min(leverage, max_leverage))
    
    return leverage
