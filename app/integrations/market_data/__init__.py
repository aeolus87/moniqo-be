"""
Market Data Integrations

Real-time and historical market data providers:
- Polygon.io WebSocket client
- (Future: Other data providers)
"""

from app.integrations.market_data.polygon_client import (
    PolygonWebSocketClient,
    MessageType,
    AssetClass,
    parse_crypto_trade,
    parse_crypto_quote,
    parse_crypto_aggregate
)

__all__ = [
    "PolygonWebSocketClient",
    "MessageType",
    "AssetClass",
    "parse_crypto_trade",
    "parse_crypto_quote",
    "parse_crypto_aggregate"
]

