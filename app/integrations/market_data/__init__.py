"""
Market Data Integrations

Real-time and historical market data providers:
- Polygon.io WebSocket client
- Binance REST API client (FREE)
- Binance WebSocket client (FREE, real-time)
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
from app.integrations.market_data.binance_ws_client import (
    BinanceWebSocketClient,
    get_binance_ws_client,
)
from app.integrations.market_data.coinlore_client import (
    CoinloreClient,
    GlobalStats,
    CoinInfo,
    get_coinlore_client,
)
from app.integrations.market_data.base import (
    MarketDataProvider,
    TickerUpdate,
    TradeUpdate,
)

__all__ = [
    # Base classes
    "MarketDataProvider",
    "TickerUpdate",
    "TradeUpdate",
    # Polygon
    "PolygonWebSocketClient",
    "MessageType",
    "AssetClass",
    "parse_crypto_trade",
    "parse_crypto_quote",
    "parse_crypto_aggregate",
    # Binance REST
    "BinanceClient",
    "Candle",
    "TickerStats",
    "get_binance_client",
    # Binance WebSocket
    "BinanceWebSocketClient",
    "get_binance_ws_client",
    # Coinlore
    "CoinloreClient",
    "GlobalStats",
    "CoinInfo",
    "get_coinlore_client",
]

