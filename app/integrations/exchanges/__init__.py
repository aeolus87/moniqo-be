"""
Exchange Integrations Package

Real exchange API integrations:
- BinanceWallet: Binance exchange integration
- (Future: CoinbaseWallet, KrakenWallet, etc.)
"""

from app.integrations.exchanges.binance_wallet import BinanceWallet

__all__ = ["BinanceWallet"]

