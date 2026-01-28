"""
Data Aggregator Service

Handles market data fetching, indicator calculation, and sentiment aggregation.

Author: Moniqo Team
"""

from typing import Optional, Dict, Any, Tuple
import time

from app.integrations.market_data import get_binance_client
from app.services.indicators import calculate_all_indicators
from app.services.signal_aggregator import get_signal_aggregator
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ==================== EXTERNAL SENTIMENT CACHE ====================
# Simple in-memory cache with timestamps for Reddit and Polymarket data
# TTL: 15 minutes (900 seconds) to avoid spamming external APIs

_external_sentiment_cache: Dict[str, Tuple[Any, float]] = {}
EXTERNAL_SENTIMENT_CACHE_TTL = 900  # 15 minutes in seconds


def get_cached_sentiment(key: str) -> Optional[Any]:
    """
    Get cached sentiment data if not expired.
    
    Args:
        key: Cache key (e.g., "reddit:BTC" or "polymarket:btc:1h")
        
    Returns:
        Cached data if valid, None if expired or not found
    """
    if key in _external_sentiment_cache:
        data, timestamp = _external_sentiment_cache[key]
        if (time.time() - timestamp) < EXTERNAL_SENTIMENT_CACHE_TTL:
            logger.debug(f"Cache hit for {key}")
            return data
        else:
            # Cache expired, remove it
            del _external_sentiment_cache[key]
            logger.debug(f"Cache expired for {key}")
    return None


def set_cached_sentiment(key: str, data: Any) -> None:
    """
    Store sentiment data in cache with current timestamp.
    
    Args:
        key: Cache key
        data: Data to cache
    """
    _external_sentiment_cache[key] = (data, time.time())
    logger.debug(f"Cache set for {key}")


async def fetch_market_data(symbol: str) -> Dict[str, Any]:
    """
    Fetch market data from Binance.
    
    Args:
        symbol: Trading symbol (e.g., "BTC/USDT")
        
    Returns:
        Dict containing candles, ticker, and price data
    """
    binance = get_binance_client()
    candles = await binance.get_klines(symbol, "1h", 100)
    ticker = await binance.get_24h_ticker(symbol)
    
    if not candles or not ticker:
        raise Exception(f"Failed to fetch market data for {symbol}")
    
    # Extract price data
    closes = [float(c.close) for c in candles]
    highs = [float(c.high) for c in candles]
    lows = [float(c.low) for c in candles]
    
    return {
        "candles": candles,
        "ticker": ticker,
        "closes": closes,
        "highs": highs,
        "lows": lows,
    }


def calculate_indicators(closes: list, highs: list, lows: list) -> Dict[str, Any]:
    """
    Calculate all technical indicators.
    
    Args:
        closes: List of close prices
        highs: List of high prices
        lows: List of low prices
        
    Returns:
        Dict containing calculated indicators
    """
    return calculate_all_indicators(closes, highs, lows)


async def fetch_aggregated_signal(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch aggregated sentiment signal from social and prediction markets.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Signal data dict or None if unavailable
    """
    try:
        base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
        aggregator = get_signal_aggregator()
        signal = await aggregator.get_signal(base_symbol.upper())
        return signal.to_dict()
    except Exception as e:
        logger.error(f"Failed to fetch sentiment signal for {symbol}: {e}")
        return None


async def fetch_polymarket_odds(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch Polymarket odds for BTC Price Up markets (with 15-min cache).
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Polymarket data dict or None if unavailable
    """
    try:
        from app.integrations.market_data.polymarket_client import get_polymarket_client
        base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
        
        if base_symbol.upper() != "BTC":
            return None
        
        # Check cache first for 1h
        cache_key_1h = "polymarket:btc:1h"
        cache_key_15m = "polymarket:btc:15m"
        
        polymarket_data = get_cached_sentiment(cache_key_1h)
        if polymarket_data is None:
            polymarket_client = get_polymarket_client()
            # Try 1h timeframe first
            polymarket_data = await polymarket_client.get_btc_price_up_odds("1h")
            if polymarket_data:
                set_cached_sentiment(cache_key_1h, polymarket_data)
                logger.info(f"Polymarket 1h data fetched and cached for {symbol}")
        
        # Fallback to 15m if 1h not found
        if polymarket_data is None:
            polymarket_data = get_cached_sentiment(cache_key_15m)
            if polymarket_data is None:
                polymarket_client = get_polymarket_client()
                polymarket_data = await polymarket_client.get_btc_price_up_odds("15m")
                if polymarket_data:
                    set_cached_sentiment(cache_key_15m, polymarket_data)
                    logger.info(f"Polymarket 15m data fetched and cached for {symbol}")
        
        return polymarket_data
    except Exception as e:
        logger.error(f"Failed to fetch Polymarket data for {symbol}: {e}")
        return None


async def fetch_reddit_sentiment(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch Reddit sentiment for symbol (with 15-min cache).
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Reddit sentiment data dict or None if unavailable
    """
    try:
        from app.integrations.market_data.reddit_client import get_reddit_client
        base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
        cache_key = f"reddit:{base_symbol.upper()}"
        
        # Check cache first
        reddit_sentiment = get_cached_sentiment(cache_key)
        if reddit_sentiment is None:
            reddit_client = get_reddit_client()
            reddit_sentiment = await reddit_client.get_symbol_sentiment(base_symbol.upper(), limit=10)
            if reddit_sentiment:
                set_cached_sentiment(cache_key, reddit_sentiment)
                logger.info(f"Reddit sentiment fetched and cached for {base_symbol.upper()}")
        
        return reddit_sentiment
    except Exception as e:
        logger.error(f"Failed to fetch Reddit sentiment for {symbol}: {e}")
        return None


async def aggregate_market_intelligence(symbol: str) -> Dict[str, Any]:
    """
    Aggregate all market intelligence: market data, indicators, and sentiment.
    
    Args:
        symbol: Trading symbol (e.g., "BTC/USDT")
        
    Returns:
        Complete market context dict
    """
    # Fetch market data
    market_data = await fetch_market_data(symbol)
    
    # Calculate indicators
    indicators = calculate_indicators(
        market_data["closes"],
        market_data["highs"],
        market_data["lows"]
    )
    
    # Build market context
    ticker = market_data["ticker"]
    market_context = {
        "symbol": symbol,
        "current_price": float(ticker.price),
        "high_24h": float(ticker.high_24h),
        "low_24h": float(ticker.low_24h),
        "change_24h_percent": float(ticker.change_percent_24h),
        "volume_24h": float(ticker.volume_24h),
    }
    
    # Fetch aggregated sentiment signal
    signal_data = await fetch_aggregated_signal(symbol)
    if signal_data:
        market_context["signal"] = signal_data
    
    # Fetch Polymarket odds
    polymarket_data = await fetch_polymarket_odds(symbol)
    if polymarket_data:
        market_context["polymarket_odds"] = polymarket_data
    
    # Fetch Reddit sentiment
    reddit_sentiment = await fetch_reddit_sentiment(symbol)
    if reddit_sentiment:
        market_context["reddit_sentiment"] = reddit_sentiment
    
    return {
        "market_context": market_context,
        "indicators": indicators,
        "candles_count": len(market_data["candles"]),
    }
