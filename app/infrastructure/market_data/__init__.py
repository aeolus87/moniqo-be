"""
Market Data Infrastructure

Market data providers and sentiment analysis clients.
"""

from app.infrastructure.market_data.base import MarketDataProvider, TickerUpdate, TradeUpdate
from app.infrastructure.market_data.sentiment_base import BaseSentimentClient, SentimentResult
from app.infrastructure.market_data.sentiment_twitter_client import TwitterSentimentClient, get_twitter_client
from app.infrastructure.market_data.reddit_sentiment_client import RedditSentimentClient, get_reddit_client
from app.infrastructure.market_data.polymarket_sentiment_client import PolymarketClient, get_polymarket_client as get_polymarket_sentiment_client
from app.infrastructure.market_data.polymarket_market_data_client import PolymarketMarketDataClient, get_polymarket_client
from app.infrastructure.market_data.reddit_market_data_client import RedditGuerrillaClient, get_reddit_client as get_reddit_market_data_client
from app.infrastructure.market_data.binance_client import BinanceClient, get_binance_client
from app.infrastructure.market_data.binance_ws_client import BinanceWebSocketClient, get_binance_ws_client
from app.infrastructure.market_data.coinlore_client import CoinloreClient, get_coinlore_client
from app.infrastructure.market_data.polygon_client import PolygonWebSocketClient

__all__ = [
    "MarketDataProvider",
    "TickerUpdate",
    "TradeUpdate",
    "BaseSentimentClient",
    "SentimentResult",
    "TwitterSentimentClient",
    "get_twitter_client",
    "RedditSentimentClient",
    "get_reddit_client",
    "PolymarketClient",
    "get_polymarket_sentiment_client",
    "PolymarketMarketDataClient",
    "get_polymarket_client",
    "RedditGuerrillaClient",
    "get_reddit_market_data_client",
    "BinanceClient",
    "get_binance_client",
    "BinanceWebSocketClient",
    "get_binance_ws_client",
    "CoinloreClient",
    "get_coinlore_client",
    "PolygonWebSocketClient",
]
