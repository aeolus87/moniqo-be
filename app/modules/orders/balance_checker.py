"""
Balance Checker Service

Pre-flight balance verification before order placement.

Author: Moniqo Team
"""

from decimal import Decimal
from typing import Dict, Any, Optional

from app.infrastructure.exchanges.base import BaseWallet
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BalanceChecker:
    """
    Balance checker that verifies sufficient funds before orders.
    
    Features:
    - Checks available balance against order requirements
    - Calculates margin requirements for leveraged trades
    - Validates against wallet minimums
    - Provides clear feedback on insufficient funds
    """
    
    # Minimum buffer to keep in account (prevent full depletion)
    MIN_BALANCE_BUFFER_PERCENT = 0.05  # Keep 5% buffer
    
    async def verify_balance(
        self,
        wallet: BaseWallet,
        symbol: str,
        quantity: Decimal,
        leverage: int = 1,
        price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Verify if wallet has sufficient balance for the order.
        
        Args:
            wallet: Wallet instance to check
            symbol: Trading symbol (e.g., "BTC/USDT")
            quantity: Order quantity
            leverage: Leverage multiplier (default 1x)
            price: Order price (fetches current if not provided)
            
        Returns:
            {
                "sufficient": bool,
                "required": float,
                "available": float,
                "margin_required": float,
                "leverage": int,
                "message": str
            }
        """
        try:
            # Get current price if not provided
            if price is None:
                price = await wallet.get_market_price(symbol)
                if price is None:
                    return {
                        "sufficient": False,
                        "required": 0.0,
                        "available": 0.0,
                        "margin_required": 0.0,
                        "leverage": leverage,
                        "message": f"Unable to fetch market price for {symbol}"
                    }
            
            # Calculate notional value
            notional_value = quantity * price
            
            # Calculate margin required (notional / leverage)
            margin_required = notional_value / Decimal(str(leverage))
            
            # Add buffer for fees and slippage (2%)
            margin_with_buffer = margin_required * Decimal("1.02")
            
            # Get available balance
            balances = await wallet.get_all_balances()
            
            # Determine quote currency (usually USDT or USD)
            quote_currency = "USDT"
            if "/" in symbol:
                quote_currency = symbol.split("/")[1]
            
            available_balance = balances.get(quote_currency, Decimal("0"))
            
            # Apply minimum buffer (keep 5% in account)
            min_buffer = available_balance * Decimal(str(self.MIN_BALANCE_BUFFER_PERCENT))
            usable_balance = available_balance - min_buffer
            
            # Check if sufficient
            sufficient = usable_balance >= margin_with_buffer
            
            result = {
                "sufficient": sufficient,
                "required": float(margin_with_buffer),
                "available": float(available_balance),
                "usable": float(usable_balance),
                "margin_required": float(margin_required),
                "notional_value": float(notional_value),
                "leverage": leverage,
                "quote_currency": quote_currency,
                "message": ""
            }
            
            if not sufficient:
                shortfall = margin_with_buffer - usable_balance
                result["message"] = (
                    f"Insufficient balance: need ${float(margin_with_buffer):.2f}, "
                    f"have ${float(usable_balance):.2f} available "
                    f"(${float(shortfall):.2f} short)"
                )
                logger.warning(
                    f"Balance check failed: {result['message']}, "
                    f"leverage={leverage}x, notional=${float(notional_value):.2f}"
                )
            else:
                result["message"] = "Balance sufficient"
            
            return result
            
        except Exception as e:
            logger.error(f"Balance check error: {str(e)}")
            return {
                "sufficient": False,
                "required": 0.0,
                "available": 0.0,
                "margin_required": 0.0,
                "leverage": leverage,
                "message": f"Balance check error: {str(e)}"
            }
    
    async def verify_order_size(
        self,
        wallet: BaseWallet,
        symbol: str,
        order_size_usd: Decimal,
        leverage: int = 1
    ) -> Dict[str, Any]:
        """
        Verify if wallet can support a USD-denominated order size.
        
        Args:
            wallet: Wallet instance to check
            symbol: Trading symbol
            order_size_usd: Order size in USD
            leverage: Leverage multiplier
            
        Returns:
            Same as verify_balance()
        """
        try:
            # Get current price
            price = await wallet.get_market_price(symbol)
            if price is None:
                return {
                    "sufficient": False,
                    "required": float(order_size_usd),
                    "available": 0.0,
                    "margin_required": 0.0,
                    "leverage": leverage,
                    "message": f"Unable to fetch market price for {symbol}"
                }
            
            # Calculate quantity from USD amount
            quantity = order_size_usd / price
            
            return await self.verify_balance(
                wallet=wallet,
                symbol=symbol,
                quantity=quantity,
                leverage=leverage,
                price=price
            )
            
        except Exception as e:
            logger.error(f"Order size verification error: {str(e)}")
            return {
                "sufficient": False,
                "required": float(order_size_usd),
                "available": 0.0,
                "margin_required": 0.0,
                "leverage": leverage,
                "message": f"Verification error: {str(e)}"
            }
    
    async def get_max_order_size(
        self,
        wallet: BaseWallet,
        symbol: str,
        leverage: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate maximum order size based on available balance.
        
        Args:
            wallet: Wallet instance
            symbol: Trading symbol
            leverage: Leverage multiplier
            
        Returns:
            {
                "max_quantity": float,
                "max_notional_usd": float,
                "available_margin": float,
                "leverage": int
            }
        """
        try:
            # Get available balance
            balances = await wallet.get_all_balances()
            
            # Determine quote currency
            quote_currency = "USDT"
            if "/" in symbol:
                quote_currency = symbol.split("/")[1]
            
            available_balance = balances.get(quote_currency, Decimal("0"))
            
            # Apply buffer
            min_buffer = available_balance * Decimal(str(self.MIN_BALANCE_BUFFER_PERCENT))
            usable_balance = available_balance - min_buffer
            
            # Calculate max notional with leverage
            max_notional = usable_balance * Decimal(str(leverage))
            
            # Account for fees (reduce by 2%)
            max_notional_after_fees = max_notional * Decimal("0.98")
            
            # Get current price for quantity calculation
            price = await wallet.get_market_price(symbol)
            max_quantity = Decimal("0")
            if price and price > 0:
                max_quantity = max_notional_after_fees / price
            
            return {
                "max_quantity": float(max_quantity),
                "max_notional_usd": float(max_notional_after_fees),
                "available_margin": float(usable_balance),
                "leverage": leverage,
                "quote_currency": quote_currency,
            }
            
        except Exception as e:
            logger.error(f"Max order size calculation error: {str(e)}")
            return {
                "max_quantity": 0.0,
                "max_notional_usd": 0.0,
                "available_margin": 0.0,
                "leverage": leverage,
                "error": str(e)
            }


# Singleton instance
_balance_checker: Optional[BalanceChecker] = None


def get_balance_checker() -> BalanceChecker:
    """Get or create balance checker instance."""
    global _balance_checker
    if _balance_checker is None:
        _balance_checker = BalanceChecker()
    return _balance_checker
