"""
Market Data Module

API endpoints for market data:
- OHLCV candlestick data
- 24h ticker statistics
- Current prices
- Global market stats
- Top cryptocurrencies

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from app.modules.market.router import router

__all__ = ["router"]
