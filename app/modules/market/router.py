"""
Market Data Router

API endpoints for market data.
No authentication required - public endpoints.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.integrations.market_data import (
    get_binance_client,
    get_coinlore_client,
)
from app.modules.market.schemas import (
    OHLCResponse,
    CandleResponse,
    TickerResponse,
    PriceResponse,
    GlobalStatsResponse,
    CoinInfoResponse,
    TopCoinsResponse,
    IndicatorsResponse,
    IndicatorValue,
    MarketDataResponse,
    MarketHealthResponse,
)
from app.services.indicators import calculate_all_indicators
from app.services.market_health import compute_market_health
from app.services.signal_aggregator import get_signal_aggregator
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/market", tags=["Market Data"])


# ==================== OHLCV DATA ====================

@router.get(
    "/ohlc/{symbol:path}",
    response_model=OHLCResponse,
    summary="Get OHLCV candles",
    description="Get candlestick data from Binance. Symbol format: BTC/USDT or BTCUSDT",
)
async def get_ohlc(
    symbol: str,
    interval: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candles"),
):
    """Get OHLCV candlestick data"""
    client = get_binance_client()
    
    try:
        candles = await client.get_klines(symbol, interval, limit)
        
        return OHLCResponse(
            symbol=symbol,
            interval=interval,
            candles=[
                CandleResponse(
                    time=c.to_dict()["time"],
                    open=c.to_dict()["open"],
                    high=c.to_dict()["high"],
                    low=c.to_dict()["low"],
                    close=c.to_dict()["close"],
                    volume=c.to_dict()["volume"],
                )
                for c in candles
            ],
        )
    except Exception as e:
        logger.error(f"Failed to fetch OHLC for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")


# ==================== MARKET DATA + HEALTH ====================

@router.get(
    "/market-data/{symbol:path}",
    response_model=MarketDataResponse,
    summary="Get combined market data",
    description="Get candles, indicators, market health, and sentiment signal",
)
async def get_market_data(
    symbol: str,
    interval: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candles"),
    include_signal: bool = Query(True, description="Include aggregated sentiment signal"),
    crash_threshold: float = Query(10.0, description="Crash threshold percent"),
):
    """Get combined market data with indicators and health"""
    client = get_binance_client()
    aggregator = get_signal_aggregator()

    try:
        candles = await client.get_klines(symbol, interval, limit)
        ticker = await client.get_24h_ticker(symbol)

        if not candles or not ticker:
            raise HTTPException(status_code=404, detail=f"Market data not found for {symbol}")

        closes = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        indicators = calculate_all_indicators(closes, highs, lows)

        health = compute_market_health(
            closes=closes,
            indicators=indicators,
            ticker_change_percent=float(ticker.change_percent_24h),
            crash_threshold=crash_threshold,
        )

        signal = None
        if include_signal:
            base_symbol = symbol.split("/")[0] if "/" in symbol else symbol
            signal = (await aggregator.get_signal(base_symbol.upper())).to_dict()

        return MarketDataResponse(
            symbol=symbol,
            interval=interval,
            candles=[
                CandleResponse(
                    time=c.to_dict()["time"],
                    open=c.to_dict()["open"],
                    high=c.to_dict()["high"],
                    low=c.to_dict()["low"],
                    close=c.to_dict()["close"],
                    volume=c.to_dict()["volume"],
                )
                for c in candles
            ],
            indicators={k: float(v) for k, v in indicators.items() if isinstance(v, (int, float))},
            current=TickerResponse(
                symbol=ticker.symbol,
                price=float(ticker.price),
                change24h=float(ticker.change_24h),
                changePercent24h=float(ticker.change_percent_24h),
                high24h=float(ticker.high_24h),
                low24h=float(ticker.low_24h),
                volume24h=float(ticker.volume_24h),
            ),
            health=MarketHealthResponse(
                symbol=symbol,
                volatility=health["volatility"],
                trend=health["trend"],
                strength=health["strength"],
                crashDetected=health["crash_detected"],
                crashThreshold=health["crash_threshold"],
            ),
            signal=signal,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch market data for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")


@router.get(
    "/market-data/{symbol:path}/health",
    response_model=MarketHealthResponse,
    summary="Get market health",
    description="Get market volatility, trend, and crash detection",
)
async def get_market_health(
    symbol: str,
    interval: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candles"),
    crash_threshold: float = Query(10.0, description="Crash threshold percent"),
):
    """Get market health metrics"""
    client = get_binance_client()

    try:
        candles = await client.get_klines(symbol, interval, limit)
        ticker = await client.get_24h_ticker(symbol)

        if not candles or not ticker:
            raise HTTPException(status_code=404, detail=f"Market data not found for {symbol}")

        closes = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        indicators = calculate_all_indicators(closes, highs, lows)

        health = compute_market_health(
            closes=closes,
            indicators=indicators,
            ticker_change_percent=float(ticker.change_percent_24h),
            crash_threshold=crash_threshold,
        )

        return MarketHealthResponse(
            symbol=symbol,
            volatility=health["volatility"],
            trend=health["trend"],
            strength=health["strength"],
            crashDetected=health["crash_detected"],
            crashThreshold=health["crash_threshold"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch market health for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch market health: {str(e)}")


# ==================== TICKER STATS ====================

@router.get(
    "/ticker/{symbol:path}",
    response_model=TickerResponse,
    summary="Get 24h ticker",
    description="Get 24h price statistics from Binance",
)
async def get_ticker(symbol: str):
    """Get 24h ticker statistics"""
    client = get_binance_client()
    
    try:
        ticker = await client.get_24h_ticker(symbol)
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker not found for {symbol}")
        
        return TickerResponse(
            symbol=ticker.symbol,
            price=float(ticker.price),
            change24h=float(ticker.change_24h),
            changePercent24h=float(ticker.change_percent_24h),
            high24h=float(ticker.high_24h),
            low24h=float(ticker.low_24h),
            volume24h=float(ticker.volume_24h),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch ticker for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch ticker: {str(e)}")


# ==================== CURRENT PRICE ====================

@router.get(
    "/price/{symbol:path}",
    response_model=PriceResponse,
    summary="Get current price",
    description="Get current price from Binance",
)
async def get_price(symbol: str):
    """Get current price"""
    client = get_binance_client()
    
    try:
        price = await client.get_price(symbol)
        
        if price is None:
            raise HTTPException(status_code=404, detail=f"Price not found for {symbol}")
        
        return PriceResponse(
            symbol=symbol,
            price=float(price),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch price for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch price: {str(e)}")


# ==================== MULTIPLE TICKERS ====================

@router.get(
    "/tickers",
    response_model=List[TickerResponse],
    summary="Get multiple tickers",
    description="Get 24h stats for multiple symbols",
)
async def get_tickers(
    symbols: str = Query(..., description="Comma-separated symbols: BTC/USDT,ETH/USDT"),
):
    """Get multiple tickers"""
    client = get_binance_client()
    
    symbol_list = [s.strip() for s in symbols.split(",")]
    
    try:
        tickers = await client.get_multiple_tickers(symbol_list)
        
        return [
            TickerResponse(
                symbol=t.symbol,
                price=float(t.price),
                change24h=float(t.change_24h),
                changePercent24h=float(t.change_percent_24h),
                high24h=float(t.high_24h),
                low24h=float(t.low_24h),
                volume24h=float(t.volume_24h),
            )
            for t in tickers
        ]
    except Exception as e:
        logger.error(f"Failed to fetch tickers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tickers: {str(e)}")


# ==================== GLOBAL STATS ====================

@router.get(
    "/global-stats",
    response_model=GlobalStatsResponse,
    summary="Get global market stats",
    description="Get global crypto market statistics from Coinlore",
)
async def get_global_stats():
    """Get global market statistics"""
    client = get_coinlore_client()
    
    try:
        stats = await client.get_global_stats()
        
        if not stats:
            raise HTTPException(status_code=500, detail="Failed to fetch global stats")
        
        return GlobalStatsResponse(
            coinsCount=stats.coins_count,
            activeMarkets=stats.active_markets,
            totalMarketCap=float(stats.total_market_cap),
            totalVolume=float(stats.total_volume),
            btcDominance=float(stats.btc_dominance),
            ethDominance=float(stats.eth_dominance),
            marketCapChange24h=float(stats.market_cap_change_24h),
            volumeChange24h=float(stats.volume_change_24h),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch global stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch global stats: {str(e)}")


# ==================== TOP COINS ====================

@router.get(
    "/top-coins",
    response_model=TopCoinsResponse,
    summary="Get top cryptocurrencies",
    description="Get top coins by market cap from Coinlore",
)
async def get_top_coins(
    start: int = Query(0, ge=0, description="Starting position"),
    limit: int = Query(20, ge=1, le=100, description="Number of coins"),
):
    """Get top coins by market cap"""
    client = get_coinlore_client()
    
    try:
        coins = await client.get_top_coins(start, limit)
        
        return TopCoinsResponse(
            coins=[
                CoinInfoResponse(
                    id=c.id,
                    symbol=c.symbol,
                    name=c.name,
                    rank=c.rank,
                    priceUsd=float(c.price_usd),
                    change1h=float(c.change_1h),
                    change24h=float(c.change_24h),
                    change7d=float(c.change_7d),
                    priceBtc=float(c.price_btc),
                    marketCap=float(c.market_cap),
                    volume24h=float(c.volume_24h),
                    circulatingSupply=float(c.circulating_supply),
                    totalSupply=float(c.total_supply),
                )
                for c in coins
            ]
        )
    except Exception as e:
        logger.error(f"Failed to fetch top coins: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch top coins: {str(e)}")


# ==================== COIN INFO ====================

@router.get(
    "/coin/{symbol}",
    response_model=CoinInfoResponse,
    summary="Get coin info",
    description="Get specific coin information by symbol",
)
async def get_coin_info(symbol: str):
    """Get coin information by symbol"""
    client = get_coinlore_client()
    
    try:
        coin = await client.get_coin_by_symbol(symbol)
        
        if not coin:
            raise HTTPException(status_code=404, detail=f"Coin not found: {symbol}")
        
        return CoinInfoResponse(
            id=coin.id,
            symbol=coin.symbol,
            name=coin.name,
            rank=coin.rank,
            priceUsd=float(coin.price_usd),
            change1h=float(coin.change_1h),
            change24h=float(coin.change_24h),
            change7d=float(coin.change_7d),
            priceBtc=float(coin.price_btc),
            marketCap=float(coin.market_cap),
            volume24h=float(coin.volume_24h),
            circulatingSupply=float(coin.circulating_supply),
            totalSupply=float(coin.total_supply),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch coin info for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch coin info: {str(e)}")


# ==================== TECHNICAL INDICATORS ====================

@router.get(
    "/indicators/{symbol:path}",
    response_model=IndicatorsResponse,
    summary="Get technical indicators",
    description="Calculate technical indicators (RSI, MACD, SMA, EMA, Bollinger Bands) from price data",
)
async def get_indicators(
    symbol: str,
    interval: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(100, ge=50, le=500, description="Number of candles for calculation"),
):
    """Calculate technical indicators for a symbol"""
    client = get_binance_client()
    
    try:
        candles = await client.get_klines(symbol, interval, limit)
        
        if len(candles) < 50:
            raise HTTPException(
                status_code=400,
                detail="Not enough data to calculate indicators (need at least 50 candles)"
            )
        
        # Extract price data
        closes = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        
        # Calculate all indicators
        result = calculate_all_indicators(closes, highs, lows)
        
        return IndicatorsResponse(
            symbol=symbol,
            interval=interval,
            indicators=[
                IndicatorValue(
                    name=ind["name"],
                    value=ind["value"],
                    signal=ind.get("signal"),
                )
                for ind in result["indicators"]
            ],
            summary=result["summary"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate indicators for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate indicators: {str(e)}")


# ==================== HEALTH CHECK ====================

@router.get(
    "/health",
    summary="Market data health check",
    description="Check connectivity to market data providers",
)
async def health_check():
    """Check market data provider connectivity"""
    binance = get_binance_client()
    coinlore = get_coinlore_client()
    
    binance_ok = await binance.test_connection()
    coinlore_ok = await coinlore.test_connection()
    
    return {
        "status": "healthy" if binance_ok and coinlore_ok else "degraded",
        "providers": {
            "binance": "connected" if binance_ok else "disconnected",
            "coinlore": "connected" if coinlore_ok else "disconnected",
        },
    }
