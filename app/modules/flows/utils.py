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
) -> Tuple[Decimal, Dict[str, Any]]:
    """Resolve order quantity using balances and sizing rules."""
    if current_price <= 0:
        raise Exception("Cannot resolve quantity without a valid current price")

    sizing_meta: Dict[str, Any] = {
        "base_balance": float(base_balance) if base_balance is not None else None,
        "quote_balance": float(quote_balance) if quote_balance is not None else None,
    }

    if order_quantity is not None:
        return order_quantity, sizing_meta

    if action == "buy":
        if quote_balance is None:
            raise Exception("Quote balance unavailable for buy sizing")
        if order_size_percent is not None:
            order_size_usd = (order_size_percent / Decimal("100")) * quote_balance
            sizing_meta["sizing_method"] = "percent"
        elif order_size_usd is None:
            order_size_usd = (default_balance_percent / Decimal("100")) * quote_balance
            sizing_meta["sizing_method"] = "default_percent"
        order_size_usd = min(order_size_usd, quote_balance)
        sizing_meta["order_size_usd"] = float(order_size_usd)
        return order_size_usd / current_price, sizing_meta

    if base_balance is None:
        raise Exception("Base balance unavailable for sell sizing")
    if order_size_percent is not None:
        sizing_meta["sizing_method"] = "percent"
        quantity = (order_size_percent / Decimal("100")) * base_balance
    elif order_size_usd is not None:
        sizing_meta["sizing_method"] = "usd"
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
