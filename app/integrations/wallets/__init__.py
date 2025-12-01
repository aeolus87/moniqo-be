"""
Wallet Integrations Package

Base wallet abstraction and implementations:
- BaseWallet: Abstract interface
- DemoWallet: Simulated trading
- BinanceWallet: Binance exchange
- (Future: CoinbaseWallet, etc.)
"""

from app.integrations.wallets.base import BaseWallet, OrderSide, OrderType, OrderStatus

__all__ = ["BaseWallet", "OrderSide", "OrderType", "OrderStatus"]

