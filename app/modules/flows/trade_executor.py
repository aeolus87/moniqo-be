"""
Trade Executor Service

Handles order placement with retries and position validation.

Author: Moniqo Team
"""

from typing import Optional, Dict, Any
from decimal import Decimal
import asyncio

from app.integrations.wallets.base import OrderSide, OrderType, TimeInForce
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def place_order_with_retry(
    wallet,
    symbol: str,
    side: OrderSide,
    order_type: OrderType,
    quantity: Decimal,
    price: Optional[Decimal],
    stop_price: Optional[Decimal],
    time_in_force: TimeInForce,
    max_retries: int,
    retry_delay_seconds: float,
) -> Dict[str, Any]:
    """
    Place an order with retries for transient failures.
    
    Args:
        wallet: Wallet instance to place order through
        symbol: Trading pair symbol
        side: BUY or SELL
        order_type: MARKET, LIMIT, etc.
        quantity: Order quantity
        price: Limit price (if applicable)
        stop_price: Stop price (if applicable)
        time_in_force: GTC, IOC, FOK, etc.
        max_retries: Maximum retry attempts
        retry_delay_seconds: Delay between retries
        
    Returns:
        Order result dict with success status, order_id, filled_quantity, etc.
    """
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            return await wallet.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force,
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "Order placement failed (attempt %s/%s): %s",
                attempt,
                max_retries,
                str(e),
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay_seconds * attempt)

    if last_error:
        raise last_error
    raise Exception("Order placement failed without error details")


async def check_price_staleness(
    wallet,
    symbol: str,
    original_price: Decimal,
    action: str,
    threshold_percent: float = 1.0,
) -> Dict[str, Any]:
    """
    Check if price has moved against the intended action.
    
    Args:
        wallet: Wallet instance to fetch fresh price from
        symbol: Trading pair symbol
        original_price: Price at time of analysis
        action: "buy" or "sell"
        threshold_percent: Maximum acceptable price movement
        
    Returns:
        Dict with is_stale flag and price_change_pct
    """
    from app.integrations.market_data.binance_client import BinanceClient
    
    fresh_price = None
    if wallet:
        try:
            fresh_price = await wallet.get_market_price(symbol)
        except Exception as e:
            logger.warning(f"Failed to refetch price from wallet: {e}")

    if fresh_price is None:
        # Fallback to Binance API
        async with BinanceClient() as binance_client:
            fresh_price = await binance_client.get_price(symbol)

    if fresh_price is None:
        logger.warning("Could not fetch fresh price for staleness check")
        return {"is_stale": False, "price_change_pct": 0, "fresh_price": None}

    fresh_price = Decimal(str(fresh_price))
    
    if original_price <= 0:
        logger.warning("Original price is zero or invalid - skipping staleness check")
        return {"is_stale": False, "price_change_pct": 0, "fresh_price": fresh_price}

    price_change_pct = float(((fresh_price - original_price) / original_price) * 100)

    # Check if price moved against us
    is_stale = False
    if action == "buy" and price_change_pct > threshold_percent:
        is_stale = True
        logger.warning(f"Price Staleness: BUY order at risk due to {price_change_pct:.2f}% price increase")
    elif action == "sell" and price_change_pct < -threshold_percent:
        is_stale = True
        logger.warning(f"Price Staleness: SELL order at risk due to {price_change_pct:.2f}% price decrease")
    else:
        logger.info(f"Price Staleness: Price change {price_change_pct:.2f}% within acceptable range")

    return {
        "is_stale": is_stale,
        "price_change_pct": price_change_pct,
        "fresh_price": fresh_price,
        "original_price": original_price,
    }


def create_simulated_order_result(
    execution_id: str,
    quantity: Decimal,
    current_price: Decimal,
    quote_asset: str = "USDT",
) -> Dict[str, Any]:
    """
    Create a simulated order result for demo mode.
    
    Args:
        execution_id: Execution ID for reference
        quantity: Order quantity
        current_price: Current market price
        quote_asset: Quote currency
        
    Returns:
        Simulated order result dict
    """
    from app.integrations.wallets.base import OrderStatus
    
    return {
        "success": True,
        "order_id": f"SIM-{execution_id}",
        "client_order_id": f"SIM-{execution_id}",
        "status": OrderStatus.FILLED.value,
        "filled_quantity": quantity,
        "average_price": current_price,
        "fee": Decimal("0"),
        "fee_currency": quote_asset,
        "simulated": True,
    }
