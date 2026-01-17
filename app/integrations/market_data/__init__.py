"""
Market Data Integrations

Real-time and historical market data providers:
- Polygon.io WebSocket client
- Binance REST API client (FREE)
- Coinlore REST API client (FREE)
"""

from app.integrations.market_data.polygon_client import (
    PolygonWebSocketClient,
    MessageType,
    AssetClass,
    parse_crypto_trade,
    parse_crypto_quote,
    parse_crypto_aggregate
)
from app.integrations.market_data.binance_client import (
    BinanceClient,
    Candle,
    TickerStats,
    get_binance_client,
)
from app.integrations.market_data.coinlore_client import (
    CoinloreClient,
    GlobalStats,
    CoinInfo,
    get_coinlore_client,
)

__all__ = [
    # Polygon
    "PolygonWebSocketClient",
    "MessageType",
    "AssetClass",
    "parse_crypto_trade",
    "parse_crypto_quote",
    "parse_crypto_aggregate",
    # Binance
    "BinanceClient",
    "Candle",
    "TickerStats",
    "get_binance_client",
    # Coinlore
    "CoinloreClient",
    "GlobalStats",
    "CoinInfo",
    "get_coinlore_client",
]

