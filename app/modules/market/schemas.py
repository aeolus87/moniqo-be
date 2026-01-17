"""
Market Data Schemas

Pydantic models for market data API responses.

Author: Moniqo Team
Last Updated: 2026-01-17
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CandleResponse(BaseModel):
    """Single candlestick data"""
    time: int = Field(..., description="Unix timestamp in seconds")
    open: float = Field(..., description="Open price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Close price")
    volume: float = Field(..., description="Volume")


class OHLCResponse(BaseModel):
    """OHLCV response"""
    symbol: str = Field(..., description="Trading pair symbol")
    interval: str = Field(..., description="Timeframe interval")
    candles: List[CandleResponse] = Field(default=[], description="List of candles")


class TickerResponse(BaseModel):
    """24h ticker statistics"""
    symbol: str = Field(..., description="Trading pair symbol")
    price: float = Field(..., description="Current price")
    change24h: float = Field(..., description="24h price change")
    changePercent24h: float = Field(..., description="24h price change percent")
    high24h: float = Field(..., description="24h high")
    low24h: float = Field(..., description="24h low")
    volume24h: float = Field(..., description="24h volume")


class PriceResponse(BaseModel):
    """Current price"""
    symbol: str = Field(..., description="Trading pair symbol")
    price: float = Field(..., description="Current price")


class GlobalStatsResponse(BaseModel):
    """Global market statistics"""
    coinsCount: int = Field(..., description="Total number of coins")
    activeMarkets: int = Field(..., description="Number of active markets")
    totalMarketCap: float = Field(..., description="Total market capitalization")
    totalVolume: float = Field(..., description="Total 24h trading volume")
    btcDominance: float = Field(..., description="Bitcoin dominance percentage")
    ethDominance: float = Field(..., description="Ethereum dominance percentage")
    marketCapChange24h: float = Field(..., description="24h market cap change")
    volumeChange24h: float = Field(..., description="24h volume change")


class CoinInfoResponse(BaseModel):
    """Coin information"""
    id: str = Field(..., description="Coin ID")
    symbol: str = Field(..., description="Coin symbol")
    name: str = Field(..., description="Coin name")
    rank: int = Field(..., description="Market cap rank")
    priceUsd: float = Field(..., description="Price in USD")
    change1h: float = Field(..., description="1h price change percent")
    change24h: float = Field(..., description="24h price change percent")
    change7d: float = Field(..., description="7d price change percent")
    priceBtc: float = Field(..., description="Price in BTC")
    marketCap: float = Field(..., description="Market capitalization")
    volume24h: float = Field(..., description="24h trading volume")
    circulatingSupply: float = Field(..., description="Circulating supply")
    totalSupply: float = Field(..., description="Total supply")


class TopCoinsResponse(BaseModel):
    """Top coins list"""
    coins: List[CoinInfoResponse] = Field(default=[], description="List of top coins")


class IndicatorValue(BaseModel):
    """Single indicator value"""
    name: str = Field(..., description="Indicator name")
    value: float = Field(..., description="Indicator value")
    signal: Optional[str] = Field(None, description="Signal interpretation (buy/sell/neutral)")


class IndicatorsResponse(BaseModel):
    """Technical indicators response"""
    symbol: str = Field(..., description="Trading pair symbol")
    interval: str = Field(..., description="Timeframe interval")
    indicators: List[IndicatorValue] = Field(default=[], description="List of indicator values")
    summary: Optional[str] = Field(None, description="Overall technical summary")
